#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ea_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  4A评估输出格式要求：
    {
      "introduction": {"background": "...", "scope": "...", "methodology": "..."},
      "business_architecture": {...},
      "application_architecture": {...},
      "data_architecture": {...},
      "technical_architecture": {...}
    }
  架构设计文档输出格式要求：
    {
      "introduction": {...},
      "business_architecture": {"diagram": "mermaid syntax", "details": "..."},
      "detailed_design": {"topology": "mermaid syntax", "modules": "...", "interfaces": "...", "data_models": "...", "deployment": "..."},
      "technical_explanation": "...",
      "security_design": "...",
      "evaluation_and_plan": "..."
    }
"""
from typing import Dict
from metagpt.actions import Action

ASSESSMENT_PROMPT = """
你是一位企业架构师，请对以下需求进行4A架构评估，输出JSON格式，要求包含：
{
  "introduction": {"background": "项目背景", "scope": "项目范围", "methodology": "参考标准"},
  "business_architecture": {"overview": "企业战略概述", "capabilities": ["能力1","能力2"], "org_structure": "mermaid语法图描述"},
  "application_architecture": {"system_overview": "...", "integration": "...", "deployment_strategy": "..."},
  "data_architecture": {"domains": ["域1","域2"], "entities": "...", "data_flow": "...", "standards": "..."},
  "technical_architecture": {"platform": "...", "deployment_design": "...", "security": "...", "scalability": "..."}
}

需求信息:
{requirements}
"""

ARCH_DESIGN_PROMPT = """
你是一位企业架构师，请依据以下4A评估结果编写详细的架构设计文档，输出JSON格式，要求包含：
{
  "introduction": {"background": "...", "scope": "...", "methodology": "..."},
  "business_architecture": {"diagram": "mermaid语法流程图", "details": "..."},
  "detailed_design": {"topology": "mermaid语法图", "modules": "...", "interfaces": "...", "data_models": "...", "deployment": "..."},
  "technical_explanation": "技术选型及规范说明",
  "security_design": "安全架构与策略",
  "evaluation_and_plan": "整体评估及后续规划"
}

4A评估结果:
{assessment}
"""

class Conduct4AAssessment(Action):
    """进行4A架构评估"""
    async def run(self, requirements: Dict) -> Dict:
        prompt = ASSESSMENT_PROMPT.format(requirements=requirements)
        assessment = await self.llm.aask(prompt)
        return assessment

class WriteArchitectureDesign(Action):
    """编写架构设计文档"""
    async def run(self, assessment: Dict) -> Dict:
        prompt = ARCH_DESIGN_PROMPT.format(assessment=assessment)
        design = await self.llm.aask(prompt)
        return design 