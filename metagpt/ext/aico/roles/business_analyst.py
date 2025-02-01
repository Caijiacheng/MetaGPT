#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : business_analyst.py
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ba_action import AnalyzeBusiness, WriteBusinessReport

class BusinessAnalyst(Role):
    """业务分析师角色,负责业务流程分析和业务架构设计"""
    
    name: str = "Frank"
    profile: str = "Business Analyst"
    goal: str = "分析业务流程,设计业务架构,确保系统满足业务需求"
    constraints: str = "严格遵循AICO的业务分析规范"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([AnalyzeBusiness])
        self._watch([WriteBusinessReport])
        
    async def _act(self) -> None:
        """处理业务分析相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, AnalyzeBusiness):
            # 处理业务分析
            raw_requirements = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
            if not raw_requirements:
                return
            analysis = await self.rc.todo.run(raw_requirements[-1])
            await self.publish(AICOEnvironment.MSG_BUSINESS_ANALYSIS, analysis)
            
        elif isinstance(msg.cause_by, WriteBusinessReport):
            # 处理业务报告
            analysis = await self.observe(AICOEnvironment.MSG_BUSINESS_ANALYSIS)
            if not analysis:
                return
            report = await self.rc.todo.run(analysis[-1])
            await self.publish(AICOEnvironment.MSG_BUSINESS_REPORT, report) 