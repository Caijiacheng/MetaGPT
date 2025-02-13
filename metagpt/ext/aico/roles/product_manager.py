#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : product_manager.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  产品经理角色负责生成PRD文档、修订PRD及设计产品，所有文档均按照 JSON 格式产出。
"""
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pdm_action import WritePRD, RevisePRD, AnalyzeRequirement, DesignProduct
from metagpt.roles import Role

class AICOProductManager(Role):
    """产品经理角色"""
    
    name: str = "Alice"
    profile: str = "Product Manager"
    goal: str = "分析用户需求，设计优秀产品"
    constraints: str = "严格遵循产品设计规范"
    
    def get_actions(self) -> list:
        return [
            ("analyze_requirement", AnalyzeRequirement),
            ("write_prd", WritePRD),
            ("revise_prd", RevisePRD),
            ("design_product", DesignProduct)
        ]
        
    async def _act(self) -> None:
        action_map = {
            AICOEnvironment.MSG_USER_REQUIREMENTS: "analyze_requirement",
            AICOEnvironment.MSG_REQUIREMENT_ANALYSIS: "write_prd",
            AICOEnvironment.MSG_ARCH_DESIGN: "revise_prd",
            AICOEnvironment.MSG_PRD: "design_product"
        }
        
        for msg in self.rc.news:
            action_name = action_map.get(msg.cause_by)
            if action_name:
                action = self.get_action(action_name)
                result = await action.run(msg.content)
                await self.publish(msg.cause_by, result)

