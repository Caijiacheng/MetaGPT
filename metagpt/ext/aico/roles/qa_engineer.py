#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : qa_engineer.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 后续补充测试计划、测试用例设计、自动化测试规范等详细要求
"""
from metagpt.roles import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.qa_action import WriteTestCase, ExecuteTest, ReportBug

class AICOQaEngineer(Role):
    """测试工程师角色,负责测试用例设计和执行"""
    
    name: str = "Quincy"
    profile: str = "QA Engineer"
    goal: str = "设计和执行测试用例,保证系统质量,及时发现和报告缺陷"
    constraints: str = "严格遵循测试规范,保证测试覆盖率"

    def get_actions(self) -> list:
        return [
            ("write_testcase", WriteTestCase),
            ("execute_test", ExecuteTest),
            ("report_bug", ReportBug)
        ]
        
    async def _act(self) -> None:
        """处理测试相关动作"""
        action_map = {
            AICOEnvironment.MSG_CODE: "write_testcase",
            AICOEnvironment.MSG_TEST_CASES: "execute_test",
            AICOEnvironment.MSG_TEST_RESULTS: "report_bug"
        }
        
        for msg in self.rc.news:
            action_name = action_map.get(msg.cause_by)
            if action_name:
                action = self.get_action(action_name)
                result = await action.run(msg.content)
                await self.publish(msg.cause_by, result)

"""
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 测试计划的具体格式和内容
    2. 测试用例的设计标准
    3. 自动化测试的覆盖率要求
    4. 缺陷严重程度的划分标准
    5. 测试环境的配置规范
    6. 验收测试的标准和流程
""" 