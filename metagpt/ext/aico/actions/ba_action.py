#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : ba_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  用户故事生成后输出JSON格式，格式要求：
    {
      "story_id": "US-001",
      "related_req_id": "REQ-001",
      "title": "故事名称",
      "description": "As a ..., I want ..., so that ...",
      "priority": "高/中/低",
      "status": "待评审",
      "acceptance_criteria": "详细标准",
      "created_time": "YYYY-MM-DD HH:mm:ss",
      "remarks": ""
    }
  业务架构分析输出JSON格式，包含以下字段：
    {
      "introduction": {"vision": "企业愿景", "goals": "业务目标", "scope": "业务范围"},
      "capabilities": ["核心能力", "支撑能力"],
      "process_design": {"diagram": "mermaid语法流程图", "description": "流程说明", "optimization": "优化建议"},
      "org_design": {"org_chart": "mermaid语法组织图", "roles": ["角色及职责"], "permissions": "权限描述"}
    }
"""
from typing import Dict
from openpyxl import load_workbook
from metagpt.actions import Action

USER_STORY_PROMPT = """
你是一位业务分析师，请将以下需求转化为用户故事，输出JSON格式，要求严格遵循以下格式：
{
  "story_id": "US-XXX",
  "related_req_id": "REQ-XXX",
  "title": "故事名称",
  "description": "As a <角色>, I want <功能> so that <价值>.",
  "priority": "高/中/低",
  "status": "待评审",
  "acceptance_criteria": "明确验收标准",
  "created_time": "YYYY-MM-DD HH:mm:ss",
  "remarks": ""
}

需求信息:
{requirements}
"""

BUSINESS_ARCHITECTURE_PROMPT = """
你是一位业务分析师，请对以下用户故事进行业务架构分析，输出JSON格式，要求包含：
{
  "introduction": {"vision": "企业愿景", "goals": "业务目标", "scope": "业务范围"},
  "capabilities": ["核心能力", "支撑能力"],
  "process_design": {"diagram": "mermaid语法流程图", "description": "流程说明", "optimization": "优化建议"},
  "org_design": {"org_chart": "mermaid语法组织图", "roles": ["角色及职责"], "permissions": "权限描述"}
}

用户故事:
{user_stories}
"""

class WriteUserStory(Action):
    """编写用户故事"""
    async def run(self, requirements_info: Dict) -> Dict:
        prompt = USER_STORY_PROMPT.format(
            requirements=requirements_info.get("requirements", "")
        )
        user_stories = await self.llm.aask(prompt)
        # 将用户故事写入Excel（具体实现略）
        tracking_file = requirements_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["用户故事管理"]
            # 写入时按照文档规范格式写入
            # 例如：ws.append([user_story["story_id"], user_story["related_req_id"], ...])
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