#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : architect.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 4A架构评估的具体评分标准和权重
    2. EA与BA在业务架构部分的协作界面
    3. 架构设计文档的评审流程和标准
    4. 技术选型决策的依据和标准
    5. 架构设计的版本控制和变更管理流程
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ea_action import Conduct4AAssessment, WriteArchitectureDesign

class AICOEnterpriseArchitect(Role):
    """企业架构师角色,负责架构设计和评估"""
    
    name: str = "Eric"
    profile: str = "Enterprise Architect"
    goal: str = "设计和评估系统架构"
    constraints: str = "遵循AICO的4A架构标准"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Conduct4AAssessment])
        self._watch([WriteArchitectureDesign])
        
    async def _act(self) -> None:
        """处理4A评估和架构设计"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, Conduct4AAssessment):
            # 处理4A评估
            parsed_reqs = await self.observe(AICOEnvironment.MSG_PARSED_REQUIREMENTS)
            if not parsed_reqs:
                return
            assessment = await self.rc.todo.run(parsed_reqs[-1])
            await self.publish(AICOEnvironment.MSG_4A_ASSESSMENT, assessment)
            
        elif isinstance(msg.cause_by, WriteArchitectureDesign):
            # 处理架构设计
            assessment = await self.observe(AICOEnvironment.MSG_4A_ASSESSMENT) 
            if not assessment:
                return
            design = await self.rc.todo.run(assessment[-1])
            await self.publish(AICOEnvironment.MSG_ARCH_DESIGN, design)
