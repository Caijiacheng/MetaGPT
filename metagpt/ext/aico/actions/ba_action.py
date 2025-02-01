#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : ba_action.py
@Modified By: Jiacheng Cai, 2023/12/15
    TODO: 需要在AICO规范中明确以下内容:
    1. 用户故事的具体格式和验收标准模板
    2. 业务架构分析的具体维度和深度要求
    3. 与EA的4A架构设计的衔接规范
"""
from typing import Dict
from openpyxl import load_workbook
from metagpt.actions import Action

USER_STORY_PROMPT = """
你是一位业务分析师,请将需求转化为用户故事。要求:

1. 用户故事格式：
- 故事ID (US-XXX格式)
- 关联需求ID
- 故事名称
- 故事描述 (As a ..., I want ..., So that ...)
- 优先级 (高/中/低)
- 状态
- 验收标准
- 创建时间
- 备注

需求信息:
{requirements}

请分析并返回JSON格式的用户故事列表,包含上述所有字段。
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
    
    async def run(self, requirements_info: Dict) -> Dict:
        # 使用LLM生成用户故事
        prompt = USER_STORY_PROMPT.format(
            requirements=requirements_info.get("requirements", "")
        )
        user_stories = await self.llm.aask(prompt)
        
        # 将用户故事写入Excel
        tracking_file = requirements_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["用户故事管理"]
            # TODO: 将user_stories写入ws
            wb.save(tracking_file)
        
        return {
            "user_stories": user_stories,
            "tracking_file": tracking_file
        }

class BusinessArchitectureAnalysis(Action):
    """业务架构分析"""
    
    async def run(self, user_stories: Dict) -> Dict:
        prompt = BUSINESS_ARCHITECTURE_PROMPT.format(user_stories=user_stories)
        ba_analysis = await self.llm.aask(prompt)
        return ba_analysis 