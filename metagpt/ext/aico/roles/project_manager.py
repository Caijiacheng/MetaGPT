#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
"""
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook, load_workbook

from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pm_action import PrepareProject, ParseRequirements, BreakDownTasks, UpdateTaskStatus

class EnterpriseProjectManager(Role):
    """项目经理角色,负责需求分解和任务管理"""
    
    name: str = "Eve"
    profile: str = "Project Manager"
    goal: str = "分解需求为任务,跟踪任务进度,确保项目按时交付"
    constraints: str = "严格遵循AICO的项目管理规范"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([PrepareProject])
        self._watch([ParseRequirements, BreakDownTasks, UpdateTaskStatus])
        self.project_phase: str = "init"  # init/planning/execution/closed
        
    async def _act(self) -> None:
        """处理项目管理相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, PrepareProject):
            # 处理项目初始化
            result = await self.rc.todo.run(
                project_name=self.rc.memory.get("project_name"),
                scope=self.rc.memory.get("scope")
            )
            self.project_phase = "planning"
            await self.publish(AICOEnvironment.MSG_PROJECT_INFO, result)
            
        elif isinstance(msg.cause_by, ParseRequirements):
            # 处理需求解析
            raw_requirements = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
            if not raw_requirements:
                return
            parsed_reqs = await self.rc.todo.run(raw_requirements[-1])
            await self._update_req_tracking(parsed_reqs)
            await self.publish(AICOEnvironment.MSG_PARSED_REQUIREMENTS, parsed_reqs)
            
        elif isinstance(msg.cause_by, BreakDownTasks):
            # 处理任务分解
            parsed_reqs = await self.observe(AICOEnvironment.MSG_PARSED_REQUIREMENTS)
            if not parsed_reqs:
                return
            tasks = await self.rc.todo.run(parsed_reqs[-1])
            await self._update_task_tracking(tasks)
            await self.publish(AICOEnvironment.MSG_TASKS, tasks)
            
        elif isinstance(msg.cause_by, UpdateTaskStatus):
            # 处理任务状态更新
            update_info = msg.content.get("update_info")
            if not update_info:
                return
            await self._update_task_status(update_info)
            
    async def _update_req_tracking(self, requirements: Dict):
        """更新需求跟踪表"""
        req_path = Path(self.rc.memory.get("doc_paths", {}).get("requirements", ""))
        if not req_path.exists():
            return
            
        wb = load_workbook(req_path)
        req_ws = wb["需求管理"]
        story_ws = wb["用户故事管理"]
        
        # 更新需求sheet
        for req in requirements.get("requirements", []):
            req_ws.append([
                f"REQ-{str(len(req_ws.rows)).zfill(3)}", 
                req.get("需求名称", ""),
                req.get("需求描述", ""),
                req.get("需求来源", ""),
                req.get("需求优先级", ""),
                "已提出",  # 初始状态
                req.get("提出人", ""),
                datetime.now().strftime("%Y-%m-%d"),
                req.get("目标完成时间", ""),
                req.get("验收标准", ""),
                req.get("备注", "")
            ])
            
        # 更新用户故事sheet
        for story in requirements.get("user_stories", []):
            story_ws.append([
                f"US-{str(len(story_ws.rows)).zfill(3)}",
                story.get("关联需求ID", ""),
                story.get("用户故事名称", ""),
                story.get("用户故事描述", ""),
                story.get("优先级", ""),
                "待开发",  # 初始状态
                story.get("验收标准", ""),
                datetime.now().strftime("%Y-%m-%d"),
                story.get("备注", "")
            ])
            
        wb.save(req_path)
        
    async def _update_task_tracking(self, tasks: List[Dict]):
        """更新任务跟踪表"""
        task_path = Path(self.rc.memory.get("doc_paths", {}).get("tasks", ""))
        if not task_path.exists():
            return
            
        wb = load_workbook(task_path)
        ws = wb.active
        
        for task in tasks:
            ws.append([
                f"T-{str(len(ws.rows)).zfill(3)}", # 任务ID
                task.get("关联需求ID", ""),
                task.get("关联用户故事ID", ""),
                task.get("任务名称", ""),
                task.get("任务描述", ""),
                task.get("任务类型", "开发"),
                task.get("负责人", ""),
                "待开始",  # 任务状态
                datetime.now().strftime("%Y-%m-%d"),  # 计划开始时间
                "",  # 计划结束时间
                "",  # 实际开始时间
                "",  # 实际结束时间
                task.get("备注", "")
            ])
        
        wb.save(task_path)
        
    async def _update_task_status(self, update_info: Dict):
        """更新任务状态"""
        task_path = Path(self.rc.memory.get("doc_paths", {}).get("tasks", ""))
        if not task_path.exists():
            return
            
        wb = load_workbook(task_path)
        ws = wb.active
        
        for row in ws.iter_rows(min_row=2):
            if row[0].value == update_info["task_id"]:
                row[7].value = update_info["status"]  # 更新状态
                if update_info["status"] == "进行中":
                    row[10].value = datetime.now().strftime("%Y-%m-%d")  # 实际开始时间
                elif update_info["status"] == "已完成":
                    row[11].value = datetime.now().strftime("%Y-%m-%d")  # 实际结束时间
                break
                
        wb.save(task_path)
