#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : dev_action.py
"""
from typing import Dict, List
from metagpt.actions import Action

CODE_PROMPT = """
你是一位资深开发工程师,请根据任务要求编写代码。要求:

1. 代码风格遵循Google规范
2. 代码结构清晰,模块化设计
3. 包含完整的类型注解
4. 包含详细的注释说明
5. 实现所有指定功能
6. 考虑异常处理
7. 遵循最佳实践

任务信息:
{task}

请编写代码并以JSON格式返回,包含:
1. 代码内容
2. 单元测试
3. 部署说明
"""

CODE_REVIEW_PROMPT = """
你是一位资深开发工程师,请对代码进行评审。评审内容包括:

1. 代码质量
   - 代码风格
   - 设计模式
   - 性能优化
   - 安全性

2. 功能完整性
   - 需求覆盖
   - 边界处理
   - 异常处理

3. 可维护性
   - 代码结构
   - 注释文档
   - 复杂度

4. 测试覆盖
   - 单元测试
   - 集成测试
   - 测试用例

代码内容:
{code}

请进行评审并返回JSON格式的评审结果,包含具体问题和改进建议。
"""

DEBUG_PROMPT = """
你是一位资深开发工程师,请根据缺陷报告进行问题诊断和修复。需要:

1. 问题分析
   - 复现步骤
   - 错误日志
   - 可能原因

2. 解决方案
   - 修复代码
   - 验证方法
   - 回归测试

3. 预防措施
   - 代码优化
   - 测试加强
   - 监控告警

缺陷报告:
{bug_report}

请进行分析和修复,返回JSON格式的结果,包含:
1. 问题分析报告
2. 修复后的代码
3. 验证方案
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