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
                              status: str = "new", role: str = None):
        """更新Excel中的原始需求状态
        
        Args:
            tracking_file: ReqTracking.xlsx 路径
            req_file: 需求文件路径
            status: 状态(new/parsed_by_ba/parsed_by_ea/completed)
            role: 角色(BA/EA)
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
            # 更新现有行
            existing_row[3].value = status  # 更新状态
            if role == "BA":
                existing_row[4].value = current_time  # 更新BA解析时间
            elif role == "EA":
                existing_row[5].value = current_time  # 更新EA解析时间
            if status == "completed":
                existing_row[6].value = current_time  # 更新完成时间
        else:
            # 添加新行
            new_row = [
                req_key,  # 需求文件
                "文档" if req_key.endswith((".md", ".txt", ".docx")) else "其他",  # 需求类型
                current_time,  # 添加时间
                status,  # 当前状态
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
            
        # 6. 等待并收集需求矩阵
        biz_requirements = await self.observe(AICOEnvironment.MSG_BIZ_REQUIREMENT_MATRIX)
        tech_requirements = await self.observe(AICOEnvironment.MSG_TECH_REQUIREMENT_MATRIX)
        
        if biz_requirements:
            # 更新BA解析状态
            self._update_raw_req_status(req_tracking, raw_req_file, 
                                      "parsed_by_ba", "BA")
            
        if tech_requirements:
            # 更新EA解析状态
            self._update_raw_req_status(req_tracking, raw_req_file, 
                                      "parsed_by_ea", "EA")
            
        if biz_requirements and tech_requirements:
            # 7. 复核需求（AI自动检查）
            requirements = {
                "business": biz_requirements[-1],
                "technical": tech_requirements[-1]
            }
            review_result = await self.rc.todo[1].run(requirements)
            
            # 新增人工确认检查（根据文档的"人工复核修正"要求）
            if not review_result.get("approved"):
                await self.publish(AICOEnvironment.MSG_REQUIREMENT_REVIEW, {
                    "status": "need_human_review",
                    "issues": review_result.get("inconsistencies")
                })
                return  # 等待人工干预
            
            # 形成需求基线后继续流程
            await self.publish(AICOEnvironment.MSG_REQUIREMENT_ANALYSIS, review_result)
            
            # 更新需求状态为完成
            self._update_raw_req_status(req_tracking, raw_req_file, "completed")
            
            # 8. 进入设计阶段（根据时序图流程）
            await self.publish(AICOEnvironment.MSG_DESIGN_PHASE_START, {
                "baseline": requirements,
                "review_result": review_result
            })
            
            # 9. 等待用户故事
            user_stories = await self.observe(AICOEnvironment.MSG_USER_STORIES)
            if user_stories:
                # 10. 制定迭代计划
                sprint_plan = await self.rc.todo[2].run({
                    "requirements": requirements,
                    "user_stories": user_stories[-1]
                })
                await self.publish(AICOEnvironment.MSG_SPRINT_PLAN, sprint_plan)
        
        # 11. 等待并复核设计文档
        designs = await self.observe(AICOEnvironment.MSG_4A_ASSESSMENT)
        if designs:
            design_review = await self.rc.todo[3].run(designs[-1])
            await self.publish(AICOEnvironment.MSG_DESIGN_REVIEW, design_review)
        
        # 12. 等待并复核任务
        tasks = await self.observe(AICOEnvironment.MSG_TASKS)
        if tasks:
            task_review = await self.rc.todo[4].run(tasks[-1])
            await self.publish(AICOEnvironment.MSG_TASK_REVIEW, task_review)
