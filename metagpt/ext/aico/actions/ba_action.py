#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ba_action.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 用户故事的具体格式和验收标准模板
    2. 业务架构分析的具体维度和深度要求
    3. 与EA的4A架构设计的衔接规范
"""
from typing import Dict
from metagpt.actions import Action

USER_STORY_PROMPT = """
你是一位业务分析师,请将需求转化为用户故事。要求:

1. 用户故事格式
   As a <用户角色>
   I want <功能描述>
   So that <价值阐述>

2. 验收标准
   - 功能验收条件
   - 业务规则
   - 异常处理

3. 优先级划分
   - 必须有(Must Have)
   - 应该有(Should Have)
   - 可以有(Could Have)

需求信息:
{requirements}

请分析并返回JSON格式的用户故事列表。
"""

BUSINESS_ARCHITECTURE_PROMPT = """
你是一位业务分析师,请对用户故事进行业务架构分析。分析内容包括:

1. 业务架构概述
   - 业务愿景
   - 业务目标
   - 业务范围

2. 业务能力分析
   - 核心能力
   - 支撑能力
   - 能力地图

3. 业务流程设计
   - 业务流程图(使用BPMN)
   - 流程说明
   - 流程优化建议

4. 组织架构设计
   - 组织结构图
   - 角色职责
   - 权限分配

用户故事:
{user_stories}

请分析并返回JSON格式的业务架构设计文档。
"""

class WriteUserStory(Action):
    """编写用户故事"""
    
    async def run(self, requirements: Dict) -> Dict:
        prompt = USER_STORY_PROMPT.format(requirements=requirements)
        user_stories = await self.llm.aask(prompt)
        return user_stories

class BusinessArchitectureAnalysis(Action):
    """业务架构分析"""
    
    async def run(self, user_stories: Dict) -> Dict:
        prompt = BUSINESS_ARCHITECTURE_PROMPT.format(user_stories=user_stories)
        ba_analysis = await self.llm.aask(prompt)
        return ba_analysis 