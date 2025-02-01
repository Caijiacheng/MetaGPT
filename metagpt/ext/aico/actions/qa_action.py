#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : qa_action.py
"""
from typing import Dict, List
from metagpt.actions import Action

TEST_CASE_PROMPT = """
你是一位资深测试工程师,请根据代码编写测试用例。测试用例需要包含:

1. 功能测试
   - 正常流程
   - 异常流程
   - 边界条件

2. 性能测试
   - 负载测试
   - 压力测试
   - 稳定性测试

3. 接口测试
   - 参数验证
   - 返回值验证
   - 异常处理

4. 安全测试
   - 权限控制
   - 数据安全
   - 漏洞检测

代码内容:
{code}

请编写测试用例并以JSON格式返回,包含:
1. 测试用例描述
2. 测试步骤
3. 预期结果
4. 测试数据
"""

EXECUTE_TEST_PROMPT = """
你是一位资深测试工程师,请执行测试用例并记录结果。需要包含:

1. 测试环境
   - 环境配置
   - 测试数据
   - 前置条件

2. 测试执行
   - 执行步骤
   - 实际结果
   - 问题记录

3. 测试报告
   - 测试结果统计
   - 问题分类统计
   - 测试结论

测试用例:
{test_cases}

请执行测试并返回JSON格式的测试报告,包含详细的执行记录和结果分析。
"""

BUG_REPORT_PROMPT = """
你是一位资深测试工程师,请根据测试结果编写缺陷报告。报告需要包含:

1. 缺陷描述
   - 问题现象
   - 影响范围
   - 优先级/严重程度

2. 复现步骤
   - 环境信息
   - 操作步骤
   - 触发条件

3. 问题分析
   - 可能原因
   - 相关日志
   - 涉及模块

4. 修复建议
   - 解决方案
   - 验证方法
   - 回归范围

测试结果:
{test_results}

请编写缺陷报告并以JSON格式返回,确保信息完整清晰。
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