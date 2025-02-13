#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
"""
from pathlib import Path
import pkg_resources

from datetime import datetime
from metagpt.roles import Role
from ..actions.pm_action import (
     ReviewAllRequirements, ReviewAllDesigns, ReviewAllTasks
)
import logging

from ..services.project_tracking_manager import ProjectTrackingManager
from ..services.version_manager import AICOVersionManager
from ..services.version_manager import get_current_version
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.ext.aico.services.doc_manager import AICODocManager,DocType
from pydantic import Field

logger = logging.getLogger(__name__)

class AICOProjectManager(Role):
    """AICO项目经理（遵循docs/aico/specs/目录下规范）"""
    
    name: str = "AICO_PM"
    profile: str = "Project Manager"
    goal: str = "根据AICO规范管理项目全生命周期"
    constraints: str = "严格遵循EA设计规范和项目管理规范"
    
    # 明确定义Pydantic字段
    project_root: Path = Field(..., description="项目根目录路径")
    doc_manager: AICODocManager = Field(default=None, description="文档管理服务")
    version_svc: AICOVersionManager = Field(default=None, description="版本管理服务")
    tracking_svc: ProjectTrackingManager = Field(default=None, description="项目跟踪服务")

    def __init__(
        self,
        project_root: Path,
        embed_model=None,
        llm=None,
        **kwargs
    ):
        # 将 project_root 转换为绝对路径，并传递给父类进行初始化
        project_root = project_root.absolute()
        super().__init__(project_root=project_root, **kwargs)
        
        # 如有需要，可把 project_root 重新赋值（实际已由父类初始化）
        self.project_root = project_root
        
        # 初始化文档管理服务（注意移除 repo= 前缀，使用位置参数传递 project_root）
        self.doc_manager = AICODocManager.from_repo(
            self.project_root,
            specs=[],
            embed_model=embed_model,
            llm=llm
        )
        
        # 初始化版本服务
        self.version_svc = AICOVersionManager.from_path(self.project_root)
        
        # 初始化跟踪服务
        self.tracking_svc = ProjectTrackingManager.from_path(
            self.doc_manager.get_path(DocType.PROJECT_TRACKING)
        )
        
        # 设置角色行为
        self.set_actions([ReviewAllRequirements, ReviewAllDesigns, ReviewAllTasks])

        self.baseline_versions = [self.version_svc.current]
        self.current_baseline_version = self.version_svc.current
        pass

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
        """需求解析流程（简化版本）"""
        try:
            await self._collect_raw_requirements()
            
            new_version = self.version_svc.bump("minor")
            self.current_baseline_version = new_version
            
            # 发布业务需求分析
            await self.publish_message(
                AICOEnvironment.MSG_REQUIREMENT_BIZ_ANALYSIS.with_content(
                    req_id=self._get_raw_requirements()["req_id"],
                    file_path=self._get_raw_requirements()["file_path"],
                    type="business",
                    version=new_version
                )
            )
            
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

        except Exception as e:
            logger.error(f"需求解析流程异常: {str(e)}")
            await self.publish_message(
                AICOEnvironment.MSG_PROCESS_FAILED.with_content(
                    process="requirement_parsing",
                    error=str(e)
                )
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
        await self.publish_message(
            AICOEnvironment.MSG_BUSINESS_ARCH.with_content(
                version=self.current_baseline_version,
                biz_requirements=self._get_parsed_biz_reqs()
            )
        )
        
        await self.publish_message(
            AICOEnvironment.MSG_TECH_ARCH.with_content(
                version=self.current_baseline_version,
                tech_requirements=self._get_parsed_tech_reqs()
            )
        )
        
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
        await self.publish_message(
            AICOEnvironment.MSG_PRD.with_content(
                version=self.current_baseline_version,
                ai_review=review_result.instruct_content,
                requirements=self._get_all_parsed_requirements()
            )
        )
        
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
        await self.publish_message(
            AICOEnvironment.MSG_PRD_REVISED.with_content(
                version=self.current_baseline_version,
                approved_reqs=confirm_msg.content["approved_reqs"],
                review_comments=confirm_msg.content.get("review_comments", {})
            )
        )

    async def _process_design(self):
        """处理设计阶段（根据文档6.2节拆分处理PRD和技术设计）"""
        # 监听设计文档完成事件
        async for design_msg in self.observe(AICOEnvironment.MSG_DESIGN_DOC_DONE.name):
            review_result = await self.rc.run(
                ReviewAllDesigns().run(design_msg.content)
            )
            
            # 根据文档类型分发处理（根据反馈点1）
            doc_type = design_msg.content.get("doc_type")
            if doc_type == "PRD":
                await self._handle_prd_design(review_result)
            elif doc_type == "TECH_DESIGN":
                await self._handle_tech_design(review_result)
            else:
                logger.warning(f"未知设计文档类型: {doc_type}")

            # 更新设计版本（根据反馈点3保持当前模式）
            new_version = self.version_svc.bump("minor")
            self.tracking_svc.update_design_version(new_version)
            
            # 发布设计基线事件（根据文档6.2.3节）
            await self.publish_message(
                AICOEnvironment.MSG_DESIGN_BASELINE.with_content(
                    version=new_version,
                    design_type=doc_type,
                    review_summary=review_result.instruct_content
                )
            )

    async def _handle_prd_design(self, review_result):
        """处理PRD设计结果"""
        self.tracking_svc.update_design_status(
            doc_type="PRD",
            status="reviewed",
            version=self.current_baseline_version
        )

    async def _handle_tech_design(self, review_result):
        """处理技术设计结果"""
        self.tracking_svc.update_design_status(
            doc_type="TECH_DESIGN",
            status="reviewed",
            version=self.current_baseline_version
        )

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
        # self.tracking_svc.save()


    def _generate_new_version(self, change_type: str) -> str:
        """完全通过VersionService生成"""
        return self.version_svc.bump(change_type)


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

    def _load_existing_specs(self):
        """加载已有项目的规范文件"""
        specs_dir = self.project_root / "docs/specs"
        return list(specs_dir.glob("*.md")) if specs_dir.exists() else []

    async def _wait_for_arch_analysis_complete(self):
        """等待架构分析完成（文档6.1.2节步骤2）"""
        # 同时等待业务架构和技术架构完成
        biz_arch_done = await self.observe(AICOEnvironment.MSG_BIZ_ARCH_DONE.name, timeout=600)
        tech_arch_done = await self.observe(AICOEnvironment.MSG_TECH_ARCH_DONE.name, timeout=600)
        
        if not biz_arch_done or not tech_arch_done:
            logger.error("架构分析超时或未完成")
            return False
        
        # 处理业务架构结果
        self._handle_ba_result(biz_arch_done.content)
        
        # 处理技术架构结果
        self._handle_ea_result(tech_arch_done.content)
        
        # 更新跟踪表状态
        self.tracking_svc.update_requirement_status(
            req_ids=[biz_arch_done.content["req_id"], tech_arch_done.content["req_id"]],
            status="arch_analyzed"
        )
        return True

    def _get_raw_requirements(self) -> dict:
        """获取原始需求数据（文档5.2节）"""
        # 从跟踪服务获取所有状态为new的需求
        return self.tracking_svc.get_requirements_by_status("new")

    def _get_parsed_biz_reqs(self) -> list:
        """获取已解析的业务需求（文档6.1.1节）"""
        return self.tracking_svc.get_requirements_by_type("business", "parsed_by_ba")

    def _get_parsed_tech_reqs(self) -> list:
        """获取已解析的技术需求（文档6.1.1节）"""
        return self.tracking_svc.get_requirements_by_type("technical", "parsed_by_ea")

    def _get_all_parsed_requirements(self) -> dict:
        """获取所有已解析需求（文档6.1.3节）"""
        return {
            "business": self._get_parsed_biz_reqs(),
            "technical": self._get_parsed_tech_reqs()
        }

