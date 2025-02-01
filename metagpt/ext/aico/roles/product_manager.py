#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : product_manager.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. PRD文档的具体模板和评审标准
    2. 产品需求变更的处理流程
    3. 与BA角色在需求分析阶段的分工
    4. 产品验收标准的制定规范
    5. 产品特性的优先级评估标准
    6. 产品文档的版本控制规范
    7. 产品需求追踪矩阵的格式
    8. 产品发布计划的制定标准
"""
from typing import Dict
from metagpt.roles.role import Role, RoleReactMode
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.actions import UserRequirement, PrepareDocuments
from ..actions.pdm_action import WritePRD, RevisePRD, AnalyzeRequirement, DesignProduct

class AICOProductManager(Role):
    """产品经理角色,负责需求分析和产品设计"""
    
    name: str = "Alice"
    profile: str = "Product Manager"
    goal: str = "分析用户需求,设计优秀产品,确保产品成功落地"
    constraints: str = "严格遵循AICO的产品设计规范和文档标准"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([PrepareDocuments, AnalyzeRequirement])
        self._watch([UserRequirement, WritePRD, RevisePRD, DesignProduct])
        self.rc.react_mode = RoleReactMode.BY_ORDER
        
    async def _act(self) -> None:
        """处理产品相关动作"""
        msg = self.rc.news[-1]
        
        if isinstance(msg.cause_by, PrepareDocuments):
            # 准备产品相关文档
            docs = await self.rc.todo.run(
                project_name=self.rc.memory.get("project_name"),
                doc_type="product"
            )
            await self.publish(AICOEnvironment.MSG_PRODUCT_DOCS, docs)
            
        elif isinstance(msg.cause_by, UserRequirement):
            # 处理用户需求
            requirements = await self.observe(AICOEnvironment.MSG_USER_REQUIREMENTS)
            if not requirements:
                return
            analysis = await self.rc.todo.run(requirements[-1])
            await self.publish(AICOEnvironment.MSG_REQUIREMENT_ANALYSIS, analysis)
            
        elif isinstance(msg.cause_by, WritePRD):
            # 编写PRD
            analysis = await self.observe(AICOEnvironment.MSG_REQUIREMENT_ANALYSIS)
            if not analysis:
                return
            prd = await self.rc.todo.run(analysis[-1])
            await self.publish(AICOEnvironment.MSG_PRD, prd)
            
        elif isinstance(msg.cause_by, RevisePRD):
            # 处理PRD修订
            arch_design = await self.observe(AICOEnvironment.MSG_ARCH_DESIGN)
            if not arch_design:
                return
            revised_prd = await self.rc.todo.run(arch_design[-1])
            await self.publish(AICOEnvironment.MSG_PRD_REVISED, revised_prd)

        elif isinstance(msg.cause_by, DesignProduct):
            # 处理产品设计
            design = await self.observe(AICOEnvironment.MSG_PRODUCT_DESIGN)
            if not design:
                return
            product = await self.rc.todo.run(design[-1])
            await self.publish(AICOEnvironment.MSG_PRODUCT_DESIGNED, product)

"""
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. PRD文档的具体模板和评审标准
    2. 产品需求变更的处理流程
    3. 与BA角色在需求分析阶段的分工
    4. 产品验收标准的制定规范
    5. 产品特性的优先级评估标准
""" 