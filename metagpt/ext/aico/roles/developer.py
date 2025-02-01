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
from .base_role import AICOBaseRole
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.dev_action import (
    PrepareEnv, DesignTechSolution, BreakdownTask,
    WriteCode, CodeReview, DebugCode, WriteUnitTest
)

class AICODeveloper(AICOBaseRole):
    """开发工程师角色"""
    
    name: str = "David"
    profile: str = "Developer"
    goal: str = "设计并实现高质量、符合规范的代码"
    constraints: str = "严格遵循代码规范、设计原则和开发流程"
    
    def get_actions(self) -> list:
        return [
            ("prepare_env", PrepareEnv),
            ("design_solution", DesignTechSolution),
            ("breakdown_task", BreakdownTask),
            ("write_code", WriteCode),
            ("code_review", CodeReview),
            ("debug_code", DebugCode),
            ("write_test", WriteUnitTest)
        ]
        
    async def _act(self) -> None:
        action_map = {
            AICOEnvironment.MSG_TASKS: "design_solution",
            AICOEnvironment.MSG_TECH_DESIGN: "breakdown_task",
            AICOEnvironment.MSG_CODE_REVIEW: "code_review",
            AICOEnvironment.MSG_BUG_REPORT: "debug_code",
            AICOEnvironment.MSG_TEST_CASES: "write_test"
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
    1. 代码规范的具体标准(目前只提到遵循Google规范)
    2. 技术方案设计文档的格式要求
    3. 代码评审的具体检查项
    4. 单元测试的覆盖率要求
    5. 开发环境的标准化配置
    6. 与QA的协作流程规范
""" 