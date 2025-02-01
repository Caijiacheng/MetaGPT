#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : product_manager.py
"""
from typing import Dict
from metagpt.roles.role import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pdm_action import WritePRD, RevisePRD

class ProductManager(Role):
    """产品经理角色,负责需求分析和PRD文档管理"""
    
    name: str = "Alice"
    profile: str = "Product Manager"
    goal: str = "分析业务需求,编写高质量的PRD文档,确保产品功能满足业务需求"
    constraints: str = "严格遵循AICO的产品设计规范"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WritePRD])
        self._watch([RevisePRD])
        
    async def _act(self) -> None:
        """处理PRD编写和修订"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, WritePRD):
            # 处理PRD编写
            parsed_reqs = await self.observe(AICOEnvironment.MSG_PARSED_REQUIREMENTS)
            if not parsed_reqs:
                return
            prd = await self.rc.todo.run(parsed_reqs[-1])
            await self.publish(AICOEnvironment.MSG_PRD, prd)
            
        elif isinstance(msg.cause_by, RevisePRD):
            # 处理PRD修订
            arch_design = await self.observe(AICOEnvironment.MSG_ARCH_DESIGN)
            if not arch_design:
                return
            revised_prd = await self.rc.todo.run(arch_design[-1])
            await self.publish(AICOEnvironment.MSG_PRD_REVISED, revised_prd) 