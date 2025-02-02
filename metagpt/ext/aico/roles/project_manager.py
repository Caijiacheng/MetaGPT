#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
说明:
  项目经理(PM)角色职责:
  1. 初始化项目,生成项目基本信息
  2. 跟踪原始需求素材的解析状态
  3. 复核业务需求和技术需求,形成需求基线
  4. 制定迭代计划,分配任务
  5. 复核设计文档,确保一致性
  6. 复核任务分解,确保可执行性
"""
from typing import Dict, List
from pathlib import Path
import json
from datetime import datetime
from openpyxl import load_workbook, Workbook
from metagpt.roles import Role
from metagpt.actions import ActionOutput
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pm_action import (
    ReviewRequirement, ReviewDesign, ReviewAllRequirements
)
from metagpt.utils.common import format_message
import logging
from metagpt.ext.aico.config import config
import shutil

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
        self._init_project()  # 项目初始化改为角色内部方法
        
    def _init_project(self):
        """初始化或加载项目结构"""
        # 项目存在性检查
        if self.project_root.exists():
            logger.info(f"加载现有项目: {self.project_root}")
            # 新增校验逻辑
            tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
            if tracking_file.exists():
                if not self._validate_tracking_file(tracking_file):
                    logger.error("项目跟踪表结构不兼容，请手动处理！")
                    raise ValueError("ProjectTracking.xlsx schema mismatch")
            self._sync_specs()
            return
        
        # 创建新项目结构
        logger.info(f"初始化新项目: {self.project_root}")
        dirs = [
            "docs/aico/specs",  # 项目专属规范目录
            "docs/ea",
            "docs/requirements",
            "tracking",
            "src",
            "config"
        ]
        for d in dirs:
            (self.project_root / d).mkdir(parents=True, exist_ok=True)
        
        self._sync_specs(force=True)  # 强制同步规范模板
        self._create_tracking_file()
        
    def _sync_specs(self, force: bool = False):
        """同步规范文件（项目规范优先于全局规范）"""
        global_spec_root = Path(config.workspace.specs)  # 全局规范路径
        project_spec_dir = self.project_root / "docs/aico/specs"
        
        # 拷贝全局规范到项目目录（不覆盖已有文件）
        for spec_file in global_spec_root.glob("*.md"):
            target = project_spec_dir / spec_file.name
            if not target.exists() or force:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(spec_file, target)
                logger.debug(f"同步规范文件: {spec_file.name}")

    def get_spec(self, spec_type: str) -> str:
        """获取规范内容（项目规范优先）"""
        project_spec = self.project_root / "docs/aico/specs" / f"{spec_type}_spec.md"
        global_spec = Path(config.workspace.specs) / f"{spec_type}_spec.md"
        
        if project_spec.exists():
            return project_spec.read_text(encoding="utf-8")
        elif global_spec.exists():
            return global_spec.read_text(encoding="utf-8")
        raise FileNotFoundError(f"规范文件不存在: {spec_type}")

    def _create_tracking_file(self):
        """创建项目跟踪表（完整结构）"""
        tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
        wb = Workbook()
        
        # 根据project_tracking_spec.md第2章定义完整表结构
        sheets = {
            "原始需求": [
                "需求文件", "需求类型", "添加时间", "当前状态", 
                "关联需求ID", "BA解析时间", "EA解析时间", 
                "完成时间", "备注"
            ],
            "需求管理": [
                "需求ID", "原始需求文件", "需求名称", "需求描述",
                "需求来源", "需求优先级", "需求状态", 
                "提出人/负责人", "提出时间", "目标完成时间",
                "验收标准", "备注"
            ],
            "用户故事管理": [
                "用户故事ID", "关联需求ID", "用户故事名称",
                "用户故事描述", "优先级", "状态", 
                "验收标准", "创建时间", "备注"
            ],
            "任务跟踪": [
                "任务ID", "关联需求ID", "关联用户故事ID",
                "任务名称", "任务描述", "任务类型",
                "负责人", "任务状态", "计划开始时间",
                "计划结束时间", "实际开始时间", 
                "实际结束时间", "备注"
            ]
        }
        
        # 删除默认创建的Sheet
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]
            
        # 创建所有工作表并添加表头
        for sheet_name, headers in sheets.items():
            ws = wb.create_sheet(sheet_name)
            ws.append(headers)
        
        wb.save(tracking_file)
        logger.info(f"创建项目跟踪表：{tracking_file}")

    async def _act(self) -> None:
        """遵循README_AICO_CN_1.2.md的时序逻辑"""
        # 阶段1：需求收集
        await self._process_requirements()
        
        # 阶段2：需求设计
        await self._process_design()
        
        # 阶段3：实现跟踪
        await self._process_implementation()

    async def _process_requirements(self):
        """处理需求收集阶段（根据文档6.1节）"""
        # 从环境获取原始需求
        req_msg = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
        if not req_msg:
            return
        
        # 将原始需求记录到跟踪表
        tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
        self._add_raw_requirement(tracking_file, req_msg.content)
        
        # 发布需求分析任务（根据文档6.1.2节）
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_ANALYSIS, {
            "requirement_id": req_msg.msg_id,
            "content": req_msg.content,
            "source": "user_input",
            "priority": "P0"
        })
        
        # 监听分析结果（根据文档6.1.3节）
        async for analysis_msg in self.observe(AICOEnvironment.MSG_PARSED_REQUIREMENTS):
            # 执行需求复核
            review_action = ReviewAllRequirements()  # 新增复合需求的Action
            review_result = await self.rc.run(review_action.run(analysis_msg.content))
            
            if review_result.instruct_content.get("need_review"):
                await self._handle_review_failure(review_result)
            else:
                # 更新需求基线（根据文档6.1.4节）
                self._update_requirement_baseline(analysis_msg.content)
                await self.publish(AICOEnvironment.MSG_REQUIREMENT_BASELINE, {
                    "version": "1.0",
                    "requirements": analysis_msg.content
                })

    def _add_raw_requirement(self, tracking_file: Path, req_data: dict):
        """将原始需求添加到跟踪表"""
        try:
            wb = load_workbook(tracking_file)
            ws = wb["原始需求"]
            
            # 生成需求ID（根据文档附录A的编号规则）
            req_id = f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 插入新行（根据project_tracking_spec.md的字段顺序）
            new_row = [
                req_data.get("file_path", ""),    # 需求文件
                req_data.get("type", "undefined"),# 需求类型
                datetime.now().isoformat(),       # 添加时间
                "待分析",                         # 当前状态
                req_id,                          # 关联需求ID（初始与自身关联）
                "",                              # BA解析时间
                "",                              # EA解析时间
                "",                              # 完成时间
                req_data.get("comment", "")      # 备注
            ]
            ws.append(new_row)
            wb.save(tracking_file)
            logger.info(f"新增原始需求: {req_id}")
            
        except Exception as e:
            logger.error(f"记录需求失败: {str(e)}")
            raise RuntimeError("需求跟踪表更新失败") from e

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
            
    def _update_tracking(self, data: dict):
        """更新跟踪表（TODO: 需要实现Excel操作）"""
        logger.debug(f"更新需求跟踪表：{format_message(data)}")
        
    def _update_task_status(self, task_info: dict):
        """更新任务状态（TODO: 需要实现Excel操作）"""
        logger.debug(f"更新任务状态：{format_message(task_info)}")

    def _load_raw_req_status(self, tracking_file: Path) -> Dict:
        """从Excel加载原始需求状态"""
        status_dict = {}
        wb = load_workbook(tracking_file)
        if "原始需求" in wb.sheetnames:
            ws = wb["原始需求"]
            headers = [cell.value for cell in ws[1]]
            for row in ws.iter_rows(min_row=2):
                values = [cell.value for cell in row]
                if not values[0]:  # 跳过空行
                    continue
                status_dict[values[0]] = {  # values[0] 是需求文件路径
                    "file": values[0],
                    "type": values[1],
                    "added_time": values[2],
                    "status": values[3],
                    "ba_parsed_time": values[4],
                    "ea_parsed_time": values[5],
                    "completed_time": values[6],
                    "notes": values[7]
                }
        return status_dict
        
    def _update_raw_req_status(self, tracking_file: Path, req_file: Path, 
                              status: str = "new", role: str = None,
                              req_id: str = None):
        """更新Excel中的原始需求状态
        
        Args:
            tracking_file: ReqTracking.xlsx 路径
            req_file: 需求文件路径
            status: 状态(new/parsed_by_ba/parsed_by_ea/completed)
            role: 角色(BA/EA)
            req_id: 关联需求ID
        """
        wb = load_workbook(tracking_file)
        ws = wb["原始需求"]
        
        # 查找现有行
        req_key = str(req_file)
        existing_row = None
        for row in ws.iter_rows(min_row=2):
            if row[0].value == req_key:
                existing_row = row
                break
                
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing_row:
            # 修复：增加状态变更校验
            if status == "parsed_by_ba" and existing_row[3].value == "parsed_by_ea":
                new_status = "completed"
            elif status == "parsed_by_ea" and existing_row[3].value == "parsed_by_ba":
                new_status = "completed"
            else:
                new_status = status
            
            existing_row[3].value = new_status  # 替换原来的直接赋值
            if req_id:
                existing_row[4].value = req_id
            if role == "BA":
                existing_row[5].value = current_time  # 更新BA解析时间
            elif role == "EA":
                existing_row[6].value = current_time  # 更新EA解析时间
            if status == "completed":
                existing_row[7].value = current_time  # 更新完成时间
        else:
            # 添加新行
            new_row = [
                req_key,  # 需求文件
                "文档" if req_key.endswith((".md", ".txt", ".docx")) else "其他",  # 需求类型
                current_time,  # 添加时间
                status,  # 当前状态
                req_id,
                current_time if role == "BA" else None,  # BA解析时间
                current_time if role == "EA" else None,  # EA解析时间
                current_time if status == "completed" else None,  # 完成时间
                ""  # 备注
            ]
            ws.append(new_row)
            
        wb.save(tracking_file)
        
    def _check_req_needs_parsing(self, tracking_file: Path, req_file: Path, role: str) -> bool:
        """检查需求是否需要解析"""
        status_dict = self._load_raw_req_status(tracking_file)
        req_key = str(req_file)
        
        if req_key not in status_dict:
            return True
            
        status = status_dict[req_key]
        if role == "BA":
            return not status.get("ba_parsed_time")
        elif role == "EA":
            return not status.get("ea_parsed_time")
        return False
        
    async def _handle_review_failure(self, review_result: Dict):
        """处理复核不通过的情况"""
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_REVIEW, {
            "req_type": "业务需求" if "business" in review_result else "技术需求",
            "status": "need_human_review",
            "issues": review_result.get("issues", []),
            "suggestions": review_result.get("suggestions", "")
        })

    async def _start_design_phase(self, parsed_requirements: Dict):
        """启动设计阶段"""
        baseline = {
            "business": parsed_requirements["business"],
            "technical": parsed_requirements["technical"],
            "user_stories": self._get_latest_msg_content(AICOEnvironment.MSG_USER_STORIES),
            "architecture": self._get_latest_msg_content(AICOEnvironment.MSG_4A_ASSESSMENT)
        }
        
        await self.publish(AICOEnvironment.MSG_DESIGN_PHASE_START, baseline)
        # 后续迭代计划流程...

    async def _get_parsed_requirement(self, msg_type: str) -> Dict:
        """获取最新解析结果"""
        msgs = await self.observe(msg_type)
        return msgs[-1] if msgs else None

    def _get_latest_msg_content(self, msg_type: str) -> Dict:
        """直接获取环境中的最新消息内容"""
        return self.rc.env.get_latest(msg_type).content if self.rc.env.get_latest(msg_type) else None

    def _validate_tracking_file(self, file_path: Path) -> bool:
        """校验跟踪表结构是否符合当前版本"""
        expected_sheets = {
            "原始需求": ["需求文件", "需求类型", "添加时间", "当前状态", "关联需求ID", "BA解析时间", "EA解析时间", "完成时间", "备注"],
            "需求管理": ["需求ID", "原始需求文件", "需求名称", "需求描述", "需求来源", "需求优先级", "需求状态", "提出人/负责人", "提出时间", "目标完成时间", "验收标准", "备注"],
            "用户故事管理": ["用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述", "优先级", "状态", "验收标准", "创建时间", "备注"],
            "任务跟踪": ["任务ID", "关联需求ID", "关联用户故事ID", "任务名称", "任务描述", "任务类型", "负责人", "任务状态", "计划开始时间", "计划结束时间", "实际开始时间", "实际结束时间", "备注"]
        }
        
        try:
            wb = load_workbook(file_path)
            for sheet_name, expected_headers in expected_sheets.items():
                if sheet_name not in wb.sheetnames:
                    logger.error(f"缺失工作表: {sheet_name}")
                    return False
                    
                ws = wb[sheet_name]
                actual_headers = [cell.value for cell in ws[1]]  # 读取第一行作为表头
                if actual_headers != expected_headers:
                    logger.error(f"工作表'{sheet_name}'结构不匹配\n期望: {expected_headers}\n实际: {actual_headers}")
                    return False
            return True
        except Exception as e:
            logger.error(f"跟踪文件校验失败: {str(e)}")
            return False

# 打印当前工作空间配置
print(config.workspace)
