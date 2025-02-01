#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
"""
from typing import Dict
from pathlib import Path
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pm_action import PrepareProject, ParseRequirements

class AICOProjectManager(Role):
    """项目经理角色,负责项目初始化和需求管理"""
    
    name: str = "Eve"
    profile: str = "Project Manager"
    goal: str = "初始化项目并管理需求"
    constraints: str = "遵循AICO项目管理规范"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([PrepareProject])
        self._watch([ParseRequirements])
        
    async def _act(self) -> None:
        """处理项目管理相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, PrepareProject):
            # 准备项目
            project_info = await self.rc.todo.run(
                idea=self.rc.memory.get("idea", ""),
                root_dir=self.rc.memory.get("output_root_dir", Path("output"))
            )
            await self.publish(AICOEnvironment.MSG_PROJECT_INFO, project_info)
            
        elif isinstance(msg.cause_by, ParseRequirements):
            # 解析需求
            project_info = await self.observe(AICOEnvironment.MSG_PROJECT_INFO)
            if not project_info:
                return
            requirements = await self.rc.todo.run(project_info[-1])
            await self.publish(AICOEnvironment.MSG_RAW_REQUIREMENTS, requirements)
