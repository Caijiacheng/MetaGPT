#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : architect.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  企业架构师角色调用 Conduct4AAssessment 与 WriteArchitectureDesign 动作，评估需求并生成架构设计文档。
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ea_action import Conduct4AAssessment, WriteArchitectureDesign

class AICOEnterpriseArchitect(Role):
    """企业架构师角色，负责架构设计和评估"""
    
    name: str = "Eric"
    profile: str = "Enterprise Architect"
    goal: str = "设计和评估系统架构"
    constraints: str = "遵循4A架构标准"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Conduct4AAssessment])
        self._watch([WriteArchitectureDesign])
        
    async def _act(self) -> None:
        msg = self.rc.news[-1]
        if isinstance(msg.cause_by, Conduct4AAssessment):
            parsed_reqs = await self.observe(AICOEnvironment.MSG_PARSED_REQUIREMENTS)
            if not parsed_reqs:
                return
            assessment = await self.rc.todo.run(parsed_reqs[-1])
            await self.publish(AICOEnvironment.MSG_4A_ASSESSMENT, assessment)
        elif isinstance(msg.cause_by, WriteArchitectureDesign):
            assessment = await self.observe(AICOEnvironment.MSG_4A_ASSESSMENT)
            if not assessment:
                return
            design = await self.rc.todo.run(assessment[-1])
            await self.publish(AICOEnvironment.MSG_ARCH_DESIGN, design)
