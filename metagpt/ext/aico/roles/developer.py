#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : developer.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  开发工程师调用 PrepareEnv、DesignTechSolution、WriteCode、CodeReview、DebugCode、WriteUnitTest 动作，确保所有产出符合新版代码规范。
"""
from typing import Dict, List
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.dev_action import (
    PrepareEnv, DesignTechSolution, BreakdownTask,
    WriteCode, CodeReview, DebugCode, WriteUnitTest
)

class AICODeveloper(Role):
    """开发工程师角色，负责技术方案设计和代码实现"""
    
    name: str = "David"
    profile: str = "Developer"
    goal: str = "设计并实现高质量、符合规范的代码"
    constraints: str = "严格遵循代码规范、设计原则和开发流程"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([PrepareEnv, DesignTechSolution])
        self._watch([BreakdownTask, WriteCode, CodeReview, DebugCode, WriteUnitTest])
        
    async def _act(self) -> None:
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, PrepareEnv):
            env_config = await self.rc.todo.run(project_type=self.rc.memory.get("project_type"))
            await self.publish(AICOEnvironment.MSG_DEV_ENV, env_config)
            
        elif isinstance(msg.cause_by, DesignTechSolution):
            tasks = await self.observe(AICOEnvironment.MSG_TASKS)
            if not tasks:
                return
            tech_design = await self.rc.todo.run(tasks[-1])
            await self.publish(AICOEnvironment.MSG_TECH_DESIGN, tech_design)
            
        elif isinstance(msg.cause_by, WriteCode):
            tasks = await self.observe(AICOEnvironment.MSG_TASKS)
            if not tasks:
                return
            code = await self.rc.todo.run(tasks[-1])
            await self.publish(AICOEnvironment.MSG_CODE, code)
            
        elif isinstance(msg.cause_by, CodeReview):
            code = await self.observe(AICOEnvironment.MSG_CODE)
            if not code:
                return
            review = await self.rc.todo.run(code[-1])
            await self.publish(AICOEnvironment.MSG_CODE_REVIEW, review)
            
        elif isinstance(msg.cause_by, DebugCode):
            bug_report = await self.observe(AICOEnvironment.MSG_BUG_REPORT)
            if not bug_report:
                return
            debug_result = await self.rc.todo.run(bug_report[-1])
            await self.publish(AICOEnvironment.MSG_DEBUG_RESULT, debug_result)
            
        elif isinstance(msg.cause_by, WriteUnitTest):
            code = await self.observe(AICOEnvironment.MSG_CODE)
            if not code:
                return
            test_result = await self.rc.todo.run(code[-1])
            await self.publish(AICOEnvironment.MSG_UNIT_TEST_RESULT, test_result)

"""
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 代码规范的具体标准(目前只提到遵循Google规范)
    2. 技术方案设计文档的格式要求
    3. 代码评审的具体检查项
    4. 单元测试的覆盖率要求
    5. 开发环境的标准化配置
    6. 与QA的协作流程规范
""" 