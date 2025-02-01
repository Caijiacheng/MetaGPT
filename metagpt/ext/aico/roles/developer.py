#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : developer.py
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.dev_action import WriteCode, CodeReview, DebugCode

class Developer(Role):
    """开发工程师角色,负责代码开发和调试"""
    
    name: str = "David"
    profile: str = "Developer"
    goal: str = "编写高质量代码,实现系统功能,确保代码可维护性"
    constraints: str = "严格遵循代码规范和最佳实践"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteCode])
        self._watch([CodeReview, DebugCode])
        
    async def _act(self) -> None:
        """处理代码开发相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, WriteCode):
            # 处理代码编写
            tasks = await self.observe(AICOEnvironment.MSG_TASKS)
            if not tasks:
                return
            code = await self.rc.todo.run(tasks[-1])
            await self.publish(AICOEnvironment.MSG_CODE, code)
            
        elif isinstance(msg.cause_by, CodeReview):
            # 处理代码评审
            code = await self.observe(AICOEnvironment.MSG_CODE)
            if not code:
                return
            review = await self.rc.todo.run(code[-1])
            await self.publish(AICOEnvironment.MSG_CODE_REVIEW, review)
            
        elif isinstance(msg.cause_by, DebugCode):
            # 处理代码调试
            bug_report = await self.observe(AICOEnvironment.MSG_BUG_REPORT)
            if not bug_report:
                return
            debug_result = await self.rc.todo.run(bug_report[-1])
            await self.publish(AICOEnvironment.MSG_DEBUG_RESULT, debug_result) 