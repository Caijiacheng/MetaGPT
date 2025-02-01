#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : business_analyst.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  当接收到原始需求时，通过调用 WriteUserStory 动作生成符合规范的用户故事。
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ba_action import WriteUserStory

class AICOBusinessAnalyst(Role):
    """业务分析师角色，负责将需求转化为用户故事"""
    
    name: str = "Frank"
    profile: str = "Business Analyst"
    goal: str = "将需求转化为符合标准的用户故事"
    constraints: str = "遵循AICO用户故事规范"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteUserStory])
        
    async def _act(self) -> None:
        msg = self.rc.news[-1]
        if isinstance(msg.cause_by, WriteUserStory):
            requirements = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
            if not requirements:
                return
            user_stories = await self.rc.todo.run(requirements[-1])
            # 此处可调用验证函数对 user_stories 格式进行校验
            await self.publish(AICOEnvironment.MSG_USER_STORIES, user_stories) 