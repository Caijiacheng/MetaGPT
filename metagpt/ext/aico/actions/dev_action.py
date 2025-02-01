#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : dev_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  代码生成输出JSON格式要求：
    {
      "code_content": "完整代码字符串",
      "unit_tests": "单元测试代码",
      "deployment_instructions": "部署说明"
    }
  代码评审输出JSON格式要求：
    {
      "issues": ["问题1", "问题2"],
      "suggestions": "改进建议描述"
    }
  调试输出格式：
    {
      "analysis_report": "问题分析",
      "fixed_code": "修改后的代码",
      "verification": "验证方案"
    }
"""
from typing import Dict, List
from metagpt.actions import Action

CODE_PROMPT = """
你是一位资深开发工程师，请根据以下任务要求编写代码，输出JSON格式，要求包含：
{
  "code_content": "完整代码字符串",
  "unit_tests": "单元测试代码",
  "deployment_instructions": "部署说明"
}

任务信息:
{task}
"""

CODE_REVIEW_PROMPT = """
你是一位资深开发工程师，请对以下代码进行评审，输出JSON格式，要求包含：
{
  "issues": ["问题1", "问题2"],
  "suggestions": "详细改进建议"
}

代码内容:
{code}
"""

DEBUG_PROMPT = """
你是一位资深开发工程师，请根据以下缺陷报告进行问题诊断和修复，输出JSON格式，要求包含：
{
  "analysis_report": "详细问题分析",
  "fixed_code": "修复后的代码",
  "verification": "验证方案"
}

缺陷报告:
{bug_report}
"""

class WriteCode(Action):
    """编写代码"""
    async def run(self, task: Dict) -> Dict:
        prompt = CODE_PROMPT.format(task=task)
        code = await self.llm.aask(prompt)
        return code

class CodeReview(Action):
    """代码评审"""
    async def run(self, code: Dict) -> Dict:
        prompt = CODE_REVIEW_PROMPT.format(code=code)
        review = await self.llm.aask(prompt)
        return review

class DebugCode(Action):
    """代码调试"""
    async def run(self, bug_report: Dict) -> Dict:
        prompt = DEBUG_PROMPT.format(bug_report=bug_report)
        debug_result = await self.llm.aask(prompt)
        return debug_result 