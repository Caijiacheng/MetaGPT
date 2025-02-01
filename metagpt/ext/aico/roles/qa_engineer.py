#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : qa_engineer.py
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.qa_action import WriteTestCase, ExecuteTest, ReportBug

class QaEngineer(Role):
    """测试工程师角色,负责测试用例设计和执行"""
    
    name: str = "Quincy"
    profile: str = "QA Engineer"
    goal: str = "设计和执行测试用例,保证系统质量,及时发现和报告缺陷"
    constraints: str = "严格遵循测试规范,保证测试覆盖率"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteTestCase])
        self._watch([ExecuteTest, ReportBug])
        
    async def _act(self) -> None:
        """处理测试相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, WriteTestCase):
            # 处理测试用例编写
            code = await self.observe(AICOEnvironment.MSG_CODE)
            if not code:
                return
            test_cases = await self.rc.todo.run(code[-1])
            await self.publish(AICOEnvironment.MSG_TEST_CASES, test_cases)
            
        elif isinstance(msg.cause_by, ExecuteTest):
            # 处理测试执行
            test_cases = await self.observe(AICOEnvironment.MSG_TEST_CASES)
            if not test_cases:
                return
            test_results = await self.rc.todo.run(test_cases[-1])
            await self.publish(AICOEnvironment.MSG_TEST_RESULTS, test_results)
            
        elif isinstance(msg.cause_by, ReportBug):
            # 处理缺陷报告
            test_results = await self.observe(AICOEnvironment.MSG_TEST_RESULTS)
            if not test_results:
                return
            bug_report = await self.rc.todo.run(test_results[-1])
            await self.publish(AICOEnvironment.MSG_BUG_REPORT, bug_report) 