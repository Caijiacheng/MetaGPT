#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : qa_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  测试用例输出格式：
    {
      "test_case_id": "TC-001",
      "description": "测试用例描述",
      "steps": ["步骤1", "步骤2"],
      "expected_results": "预期结果说明",
      "test_data": "测试数据描述"
    }
  测试报告输出格式：
    {
      "environment": "测试环境描述",
      "execution_steps": ["步骤1", "步骤2"],
      "actual_results": "实际结果描述",
      "issues_found": ["问题说明"],
      "conclusion": "测试结论说明"
    }
  缺陷报告输出格式：
    {
      "bug_id": "BUG-001",
      "description": "缺陷描述",
      "reproduction_steps": ["步骤1", "步骤2"],
      "analysis": "问题分析",
      "fix_suggestions": "修复建议"
    }
"""
from typing import Dict, List
from metagpt.actions import Action

TEST_CASE_PROMPT = """
你是一位资深测试工程师，请根据以下代码编写测试用例，输出JSON格式，要求格式如下：
{
  "test_case_id": "TC-XXX",
  "description": "测试用例描述",
  "steps": ["详细步骤"],
  "expected_results": "预期结果描述",
  "test_data": "测试数据描述"
}

代码内容:
{code}
"""

EXECUTE_TEST_PROMPT = """
你是一位资深测试工程师，请执行以下测试用例，并记录测试结果，输出JSON格式，要求格式如下：
{
  "environment": "测试环境描述",
  "execution_steps": ["执行步骤"],
  "actual_results": "实际结果描述",
  "issues_found": ["发现的问题"],
  "conclusion": "测试结论"
}

测试用例:
{test_cases}
"""

BUG_REPORT_PROMPT = """
你是一位资深测试工程师，请根据以下测试结果编写缺陷报告，输出JSON格式，要求格式如下：
{
  "bug_id": "BUG-XXX",
  "description": "缺陷描述",
  "reproduction_steps": ["复现步骤"],
  "analysis": "问题分析",
  "fix_suggestions": "修复建议"
}

测试结果:
{test_results}
"""

class WriteTestCase(Action):
    """编写测试用例"""
    async def run(self, code: Dict) -> Dict:
        prompt = TEST_CASE_PROMPT.format(code=code)
        test_cases = await self.llm.aask(prompt)
        return test_cases

class ExecuteTest(Action):
    """执行测试"""
    async def run(self, test_cases: Dict) -> Dict:
        prompt = EXECUTE_TEST_PROMPT.format(test_cases=test_cases)
        test_results = await self.llm.aask(prompt)
        return test_results

class ReportBug(Action):
    """报告缺陷"""
    async def run(self, test_results: Dict) -> Dict:
        prompt = BUG_REPORT_PROMPT.format(test_results=test_results)
        bug_report = await self.llm.aask(prompt)
        return bug_report 