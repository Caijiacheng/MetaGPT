#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : business_analyst.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 用户故事的格式规范和验收标准
    2. BA与EA在4A架构设计中的具体分工界面
    3. 业务架构(BA)部分的具体输出规范和模板
    4. BA角色在整个AICO流程中的输入输出关系
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ba_action import WriteUserStory, BusinessArchitectureAnalysis

class BusinessAnalyst(Role):
    """业务分析师角色,负责需求转化和业务架构分析"""
    
    name: str = "Frank"
    profile: str = "Business Analyst"
    goal: str = "将需求转化为用户故事,完成业务架构分析"
    constraints: str = "遵循AICO的业务分析规范和4A架构标准"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteUserStory])
        self._watch([BusinessArchitectureAnalysis])
        
    async def _act(self) -> None:
        """处理业务分析相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, WriteUserStory):
            # 处理用户故事编写
            raw_requirements = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
            if not raw_requirements:
                return
            user_stories = await self.rc.todo.run(raw_requirements[-1])
            await self.publish(AICOEnvironment.MSG_USER_STORIES, user_stories)
            
        elif isinstance(msg.cause_by, BusinessArchitectureAnalysis):
            # 处理业务架构分析
            user_stories = await self.observe(AICOEnvironment.MSG_USER_STORIES)
            if not user_stories:
                return
            ba_analysis = await self.rc.todo.run(user_stories[-1])
            await self.publish(AICOEnvironment.MSG_BUSINESS_ARCHITECTURE, ba_analysis) 