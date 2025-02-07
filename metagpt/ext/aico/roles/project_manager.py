#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
"""
from pathlib import Path

from datetime import datetime
from metagpt.roles import Role
from ..actions.pm_action import (
    ReviewRequirement, ReviewDesign, ReviewAllRequirements
)
import logging
from metagpt.ext.aico.config import config
import shutil
from ..services.project_tracking_manager import ProjectTrackingManager
from ..services.version_manager import AICOVersionManager
from ..services.version_manager import get_current_version
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.ext.aico.services.doc_manager import DocManagerService, DocType

logger = logging.getLogger(__name__)

class AICOProjectManager(Role):
    """AICO项目经理（遵循docs/aico/specs/目录下规范）"""
    
    name: str = "AICO_PM"
    profile: str = "Project Manager"
    goal: str = "根据AICO规范管理项目全生命周期"
    constraints: str = "严格遵循EA设计规范和项目管理规范"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewRequirement, ReviewDesign, ReviewAllRequirements])  # 只保留需要LLM交互的Action
        self.version_svc = AICOVersionManager(self.project_root)  # 注入项目根目录
        self.baseline_versions = [self.version_svc.current]
        self.current_baseline_version = self.version_svc.current
        self.doc_manager = DocManagerService(self.project_root)
        
    def _init_project(self):
        """使用DocManagerService管理目录结构"""
        if self.project_root.exists():
            logger.info(f"加载现有项目: {self.project_root}")
            self._validate_project_structure()
            self._sync_specs()
            return

        # 创建新项目结构（通过DocManagerService）
        logger.info(f"初始化新项目结构: {self.project_root}")
        
        # 确保基础目录存在
        self.doc_manager.ensure_dirs([
            DocType.REQUIREMENT_RAW,
            DocType.REQUIREMENT_ANALYZED,
            DocType.BUSINESS_ARCH,
            DocType.TECH_ARCH,
            DocType.PRD,
            DocType.SERVICE_DESIGN,
            DocType.TEST_CASE
        ])
        
        # 创建跟踪表（通过服务类）
        self._create_tracking_file()
        logger.info("项目结构初始化完成")

    def _validate_project_structure(self):
        """校验目录结构符合规范"""
        # 使用DocType枚举定义需要校验的目录类型
        required_doc_types = [
            DocType.REQUIREMENT_RAW,
            DocType.REQUIREMENT_ANALYZED,
            DocType.BUSINESS_ARCH,
            DocType.TECH_ARCH,
            DocType.PRD,
            DocType.SERVICE_DESIGN,
            DocType.TEST_CASE,
            DocType.PROJECT_TRACKING
        ]
        
        missing_dirs = []
        for doc_type in required_doc_types:
            # 通过DocManagerService获取标准路径（不带版本号）
            expected_path = self.doc_manager.get_doc_path(
                doc_type=doc_type,
                version="",  # 基础目录不需要版本号
                create_dir=False
            )
            # 转换为相对于项目根目录的路径
            relative_path = expected_path.relative_to(self.project_root)
            
            if not expected_path.exists():
                missing_dirs.append(str(relative_path))

        if missing_dirs:
            logger.error(f"项目结构不完整，缺失目录: {missing_dirs}")
            raise ValueError("Invalid project structure")



    def _create_tracking_file(self):
        """通过DocManagerService获取跟踪表路径"""
        tracking_path = self.doc_manager.get_doc_path(
            DocType.PROJECT_TRACKING,
            version=""
        )
        self.tracking_svc = ProjectTrackingManager(tracking_path)
        self.tracking_svc.save()

    async def _act(self) -> None:
        """遵循README_AICO_CN_1.2.md的时序逻辑"""
        # 阶段1：需求收集
        await self._process_requirements()
        
        # 阶段2：需求设计
        await self._process_design()
        
        # 阶段3：实现跟踪
        await self._process_implementation()

    async def _process_requirements(self):
        """严格遵循文档6.1节的时序"""
        # 阶段1：原始需求解析
        await self._parse_raw_requirements()
        
        # 阶段2：架构分析
        await self._process_arch_analysis()
        
        # 阶段3：基线确认
        await self._confirm_requirement_baseline()

    async def _parse_raw_requirements(self):
        """需求解析流程"""
        await self._collect_raw_requirements()
        
        new_version = self.version_svc.bump("minor")
        self.current_baseline_version = new_version
        
        # 发布业务需求分析
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_BIZ_ANALYSIS.name, {
            "req_id": self._get_raw_requirements()["req_id"],
            "file_path": self._get_raw_requirements()["file_path"],
            "type": "business",
            "version": new_version
        })
        
        # 等待BA分析完成
        analysis_done = await self.observe(AICOEnvironment.MSG_BA_ANALYSIS_DONE.name)
        if analysis_done:
            self._handle_ba_result(analysis_done.content)
            
            # 更新跟踪表
            self.tracking_svc.update_requirements_version(
                req_ids=[analysis_done.content["req_id"]],
                version=new_version
            )
            
            # 更新需求状态
            self.tracking_svc.update_raw_requirement_status(
                req_id=analysis_done.content["req_id"],
                status="parsed_by_ba"
            )

    async def _collect_raw_requirements(self):
        """严格遵循文档5.2节原始需求跟踪流程"""
        # 处理启动参数传入的需求
        if self.rc.env.requirements:
            for req in self.rc.env.requirements:
                await self._process_input_requirement(req)
        
        # 扫描未登记需求（文档5.2节步骤4）
        self._scan_unregistered_reqs()

    async def _process_input_requirement(self, req_input: dict):
        """统一处理各种输入方式的需求（文档5.2节步骤2）"""
        # 处理文件输入
        if "file_path" in req_input:
            saved_path = self._save_requirement_file(req_input["file_path"])
            self._add_to_tracking(saved_path, req_input)
        # 处理文本输入
        elif "text" in req_input:
            saved_path = self._save_requirement_text(req_input["text"])
            self._add_to_tracking(saved_path, req_input)
        else:
            logger.error("无效的需求输入格式")

    def _save_requirement_text(self, text: str) -> Path:
        """保存文本需求到文件"""
        return self.doc_manager.save_document(
            doc_type=DocType.REQUIREMENT_RAW,
            content=text,
            version=""  # 原始需求不需要版本号
        )
    
    def _save_requirement_file(self, src_path: str) -> Path:
        """保存需求文件"""
        content = Path(src_path).read_text(encoding="utf-8")
        return self.doc_manager.save_document(
            doc_type=DocType.REQUIREMENT_RAW,
            content=content,
            version=""
        )

    def _add_to_tracking(self, file_path: Path, req_data: dict):
        """添加需求到跟踪表（文档5.2节步骤5）"""
        relative_path = str(file_path.relative_to(self.project_root))
        
        self.tracking_svc.add_raw_requirement(
            file_path=relative_path,
            description=req_data.get("description", ""),
            source=req_data.get("source", "manual"),
            req_type=req_data.get("type", "business")  # 区分业务/技术需求
        )
        logger.info(f"需求已登记到跟踪表: {file_path.name}")

    async def _process_arch_analysis(self):
        """架构分析流程"""
        await self.publish(AICOEnvironment.MSG_BUSINESS_ARCH.name, {
            "version": self.current_baseline_version,
            "biz_requirements": self._get_parsed_biz_reqs()
        })
        
        await self.publish(AICOEnvironment.MSG_TECH_ARCH.name, {
            "version": self.current_baseline_version,
            "tech_requirements": self._get_parsed_tech_reqs()
        })
        
        # 等待架构分析完成
        await self._wait_for_arch_analysis_complete()

    async def _confirm_requirement_baseline(self):
        """需求基线确认（文档6.1.3节）"""
        # 执行需求评审（AI预审）
        review_result = await self.rc.run(ReviewAllRequirements().run(
            context={
                "version": self.current_baseline_version,
                "requirements": self._get_all_parsed_requirements()
            }
        ))
        
        # 等待人工确认（新增）
        await self.publish("project:req_review_ready", {
            "version": self.current_baseline_version,
            "ai_review": review_result.instruct_content,
            "requirements": self._get_all_parsed_requirements()
        })
        
        # 监听人工确认结果（新增）
        confirm_msg = await self.observe("project:req_review_confirmed", timeout=3600)
        if not confirm_msg or not confirm_msg.content.get("approved"):
            logger.error("需求基线确认未通过")
            return
        
        # 更新跟踪表（记录审核信息）
        self.tracking_svc.mark_requirements_as_baselined(
            version=self.current_baseline_version,
            req_ids=confirm_msg.content["approved_reqs"],
            review_info={
                "reviewer": confirm_msg.content.get("reviewer", "人工审核"),
                "comment": confirm_msg.content.get("comment", ""),
                "review_time": datetime.now().isoformat()
            }
        )
        
        # 发布基线确认事件（携带审核信息）
        await self.publish("project:req_baseline_confirmed", {
            "version": self.current_baseline_version,
            "approved_reqs": confirm_msg.content["approved_reqs"],
            "review_details": confirm_msg.content
        })

    async def _process_design(self):
        """处理设计阶段"""
        design_msg = await self.observe("design_doc")
        if design_msg:
            review_result = await self.rc.run(
                ReviewDesign().run(design_msg.content)
            )
            
            # 发布设计基线（根据文档6.2节）
            await self.publish("design:baseline", {
                "prd": design_msg.content,
                "review": review_result.instruct_content
            })

    async def _process_implementation(self):
        """处理实现跟踪（根据文档6.3节）"""
        # 监听任务相关消息并更新跟踪表
        async for msg in self.observe("task_update"):
            self._update_task_status(msg.content)
            if msg.content.get("artifacts"):
                self.tracking_svc.update_task_artifacts(
                    task_id=msg.content["task_id"],
                    artifacts=msg.content["artifacts"]
                )

        async for msg in self.observe("task_done"):
            if msg.content.get("artifacts"):
                self.tracking_svc.update_task_artifacts(
                    msg.content["task_id"],
                    msg.content["artifacts"]
                )

    def _validate_tracking_file(self) -> bool:
        """校验跟踪表结构（改为通过服务类）"""
        try:
            # 服务类内部实现校验逻辑
            self.tracking_svc._get_workbook()
            return True
        except Exception as e:
            logger.error(f"跟踪文件校验失败: {str(e)}")
            return False

    def get_requirement_status(self, req_id: str) -> dict:
        """获取需求状态"""
        return self.tracking_svc.get_requirement_status(req_id)

    def update_task_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        self.tracking_svc.update_task_progress(task_id, progress)
        self.tracking_svc.save()

    def _clean_old_versions(self):
        """清理逻辑改为基于VERSION文件"""
        current_version = get_current_version(self.project_root)
        vs = AICOVersionManager.from_version(current_version)
        
        # 根据当前版本计算保留范围
        retention_policy = {
            "major": vs.major - 2 if vs.major > 2 else 0,
            "minor": 3,
            "patch": 2
        }
        self.tracking_svc.clean_old_versions(retention_policy)

    def _generate_new_version(self, change_type: str) -> str:
        """完全通过VersionService生成"""
        return self.version_svc.bump(change_type)

    def generate_version_report(self, version: str) -> str:
        """生成版本变更报告"""
        history = self.tracking_svc.get_version_history()
        target = next((h for h in history if h["version"] == version), None)
        
        if not target:
            return f"版本 {version} 未找到"
        
        report = f"# 版本变更报告 ({version})\n\n"
        report += f"**生成时间**: {target['time']}\n"
        report += f"**关联文档**: [{target['doc_path']}]({target['doc_path']})\n\n"
        
        report += "## 主要变更\n"
        for change in target["changes"]:
            report += f"- {change}\n"
        
        report += "\n## 关联需求\n"
        for req_id in target["related_reqs"]:
            req_info = self.tracking_svc.get_requirement_info(req_id)
            report += f"- {req_id}: {req_info.get('description', '')}\n"
            
            req_status = self.tracking_svc.get_requirement_status(req_id)
            if req_status != "评审通过":
                logger.warning(f"需求 {req_id} 状态异常")
        
        return report

    def _determine_version_change(self) -> str:
        """根据文档6.1.3判断版本变更类型"""
        changes = self.tracking_svc.get_pending_changes()
        
        if any(c["change_type"] == "架构变更" for c in changes):
            return "major"
        elif any(c["change_type"] == "新增功能" for c in changes):
            return "minor"
        return "patch"

    def _create_version_dirs(self, version: str):
        """使用DocManagerService创建版本目录"""
        doc_types = [
            DocType.REQUIREMENT_ANALYZED,
            DocType.BUSINESS_ARCH,
            DocType.TECH_ARCH,
            DocType.PRD,
            DocType.SERVICE_DESIGN,
            DocType.TEST_CASE
        ]
        
        for doc_type in doc_types:
            self.doc_manager.get_doc_path(
                doc_type=doc_type,
                version=version,
                create_dir=True
            )

    def _init_version_documents(self, version: str):
        """在首个正式版本创建需求文档"""
        req_dir = self.project_root / f"docs/requirements/analyzed/{version}/req-001"
        req_dir.mkdir()
        
        # 需求文档模板
        (req_dir / "biz_analysis.md").write_text("# 业务需求分析模板")
        
        # 同步创建其他文档模板...

    def _all_requirements_analyzed(self) -> bool:
        """检查所有需求是否完成分析"""
        reqs = self.tracking_svc.get_all_requirements()
        return all(
            req["ba_status"] == "完成" and req["ea_status"] == "完成"
            for req in reqs
        )

    def _get_baseline_reqs(self) -> list:
        """获取基线需求列表"""
        return [
            {
                "id": req["req_id"],
                "type": req["type"],
                "description": req["description"][:100]  # 截断长描述
            }
            for req in self.tracking_svc.get_approved_requirements()
        ]

    def _handle_ba_result(self, result: dict):
        """处理BA分析结果"""
        # 更新需求跟踪
        self.tracking_svc.update_requirement(
            req_id=result["req_id"],
            updates={
                "standard_req": result["standard_req"],
                "user_stories": result["user_stories"],
                "output_files": result["output_files"]
            }
        )

    def _handle_ea_result(self, msg):
        """处理EA分析结果（文档6.1.2步骤3）"""
        self.tracking_svc.update_requirement(
            req_id=msg.content["req_id"],
            updates={
                "ea_status": "完成",
                "ea_design": msg.content["design_doc"]
            }
        )

    def _scan_unregistered_reqs(self):
        """扫描未登记需求（文档5.2节步骤4）"""
        raw_dir = self.project_root / "docs/requirements/raw"
        tracked_files = self.tracking_svc.get_tracked_files()
        
        for req_file in raw_dir.glob("*.md"):
            if str(req_file.relative_to(raw_dir)) not in tracked_files:
                logger.warning(f"发现未登记需求文件: {req_file}")
                self._add_to_tracking(req_file, {
                    "description": req_file.read_text()[:100],
                    "source": "file_scan"
                })

    def _update_task_status(self, task_info: dict):
        """更新任务状态（文档6.3.2）"""
        self.tracking_svc.update_task(
            task_id=task_info["task_id"],
            updates={
                "status": task_info["status"],
                "progress": task_info.get("progress", 0)
            }
        )



