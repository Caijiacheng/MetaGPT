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
from openpyxl import load_workbook
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pm_action import (
    PrepareProject, ReviewAllRequirements,
    PlanSprintReleases, ReviewAllDesigns, ReviewAllTasks
)
from .base_role import AICOBaseRole
from metagpt.ext.aico.services.spec_service import SpecService

class AICOProjectManager(AICOBaseRole):
    """项目经理角色,负责项目管理和需求管理"""
    
    name: str = "Eve"
    profile: str = "Project Manager"
    goal: str = "管理项目并确保需求、设计、任务的质量"
    constraints: str = "遵循AICO项目管理规范"
    
    def get_actions(self) -> list:
        """定义PM角色的Action执行顺序"""
        return [
            ("prepare_project", PrepareProject),
            ("review_requirements", ReviewAllRequirements),
            ("plan_sprints", PlanSprintReleases),
            ("review_designs", ReviewAllDesigns),
            ("review_tasks", ReviewAllTasks)
        ]
        
    def __init__(self, project_info: Dict = None, **kwargs):
        super().__init__(**kwargs)
        self.project_info = project_info or {}
        
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
        
    async def _act(self) -> None:
        """PM角色的行为逻辑"""
        # 规范同步（使用新接口）
        spec_service = SpecService(self.project_info["project_root"])
        
        # 同步所有注册的规范类型
        sync_results = {}
        for spec_type in SpecService.VALID_SPEC_TYPES:
            sync_results[spec_type] = spec_service.sync_global_spec(spec_type)
        
        # 获取最新合并规范
        current_specs = {
            st: spec_service.get_spec(st) 
            for st in SpecService.VALID_SPEC_TYPES
        }
        
        # 更新到项目配置
        self.project_info["specs"] = current_specs
        
        # 初始化时检查规范版本
        ea_versions = spec_service.get_spec_version("ea_design")
        
        # 提示版本差异
        if len(ea_versions) > 1:
            self.logger.warning(f"检测到架构规范版本差异:\n" + "\n".join(
                [f"{k}: {v}" for k, v in ea_versions.items()]
            ))
        
        # 优先使用项目规范
        current_spec = spec_service.get_spec("ea_design")
        
        # 修复：增加缺失的Sheet初始化
        init_action = self.get_action("prepare_project")
        await init_action.run({
            "project_name": "AICO项目",
            "tracking_file": "ProjectTracking.xlsx",
            "sheets_config": {  # 新增配置
                "原始需求": ["需求文件", "需求类型", "添加时间", "当前状态", "关联需求ID", 
                          "BA解析时间", "EA解析时间", "完成时间", "备注"],
                "需求管理": ["需求ID", "原始需求文件", "需求名称", "需求描述", "需求来源",
                          "需求优先级", "需求状态", "提出人/负责人", "提出时间", "目标完成时间",
                          "验收标准", "备注"],
                "用户故事管理": ["用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述",
                             "优先级", "状态", "验收标准", "创建时间", "备注"],
                "任务跟踪": ["任务ID", "关联需求ID", "关联用户故事ID", "任务名称", "任务描述",
                          "任务类型", "负责人", "任务状态", "计划开始时间", "计划结束时间",
                          "实际开始时间", "实际结束时间", "备注"]
            }
        })
        
        # 任务跟踪时读取统一文件
        tasks = await self.observe(AICOEnvironment.MSG_TASKS)
        if tasks:
            tracking_file = Path("ProjectTracking.xlsx")
            wb = load_workbook(tracking_file)
            task_sheet = wb["任务跟踪"]
            # ...任务处理逻辑...
        
        # 通过self.get_action(name)获取具体Action
        prepare_action = self.get_action("prepare_project")
        project_config = await prepare_action.run(self.project_info)
        
        # 2. 处理当前需求
        raw_req_file = Path(project_config["raw_requirement"])
        req_tracking = project_config["req_tracking"]
        
        # 3. 更新需求状态为新建
        self._update_raw_req_status(req_tracking, raw_req_file, "new")
        
        # 4. 发布项目信息
        await self.publish(AICOEnvironment.MSG_PROJECT_INFO, project_config)
        
        # 5. 通知BA/EA处理需求(仅当需要解析时)
        if self._check_req_needs_parsing(req_tracking, raw_req_file, "BA"):
            await self.publish(AICOEnvironment.MSG_RAW_REQUIREMENTS, {
                "file": str(raw_req_file),
                "role": "BA",
                "tracking_file": req_tracking
            })
            
        if self._check_req_needs_parsing(req_tracking, raw_req_file, "EA"):
            await self.publish(AICOEnvironment.MSG_RAW_REQUIREMENTS, {
                "file": str(raw_req_file),
                "role": "EA",
                "tracking_file": req_tracking
            })
            
        # 6. 收集所有需求解析结果
        parsed_requirements = {
            "business": await self._get_parsed_requirement(AICOEnvironment.MSG_BIZ_REQUIREMENT_MATRIX),
            "technical": await self._get_parsed_requirement(AICOEnvironment.MSG_TECH_REQUIREMENT_MATRIX)
        }
        
        # 7. 统一复核需求（无论是否存在业务/技术需求）
        if any(parsed_requirements.values()):
            review_action = self.get_action("review_requirements")
            review_result = await review_action.run({
                "raw_requirement": raw_req_file,  # 从文件读取的原始内容
                "parsed_requirements": parsed_requirements,
                "user_stories": self._get_latest_msg_content(AICOEnvironment.MSG_USER_STORIES),
                "business_arch": self._get_latest_msg_content(AICOEnvironment.MSG_BUSINESS_ARCHITECTURE),
                "tech_arch": self._get_latest_msg_content(AICOEnvironment.MSG_4A_ASSESSMENT)
            })
            
            if not review_result.get("approved"):
                await self._handle_review_failure(review_result)
                return
            
            # 8. 更新需求状态
            if parsed_requirements["business"]:
                self._update_raw_req_status(req_tracking, raw_req_file, "parsed_by_ba", "BA")
            if parsed_requirements["technical"]:
                self._update_raw_req_status(req_tracking, raw_req_file, "parsed_by_ea", "EA")
            
            # 9. 进入设计阶段（根据实际存在的需求类型）
            await self._start_design_phase(parsed_requirements)
        
        # 11. 等待并复核设计文档
        designs = await self.observe(AICOEnvironment.MSG_4A_ASSESSMENT)
        if designs:
            design_review_action = self.get_action("review_designs")
            design_review = await design_review_action.run(designs[-1])
            await self.publish(AICOEnvironment.MSG_DESIGN_REVIEW, design_review)
        
        # 12. 等待并复核任务
        tasks = await self.observe(AICOEnvironment.MSG_TASKS)
        if tasks:
            task_review_action = self.get_action("review_tasks")
            task_review = await task_review_action.run(tasks[-1])
            await self.publish(AICOEnvironment.MSG_TASK_REVIEW, task_review)

        # 检查规范版本
        project_spec = Path(self.project_info["spec_dir"]) / "EA-Design.md"
        global_spec = Path("docs/aico/specs/EA-Design.md")
        
        if project_spec.stat().st_mtime < global_spec.stat().st_mtime:
            self.logger.warning(f"项目规范 {project_spec} 版本较旧，建议更新")

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
