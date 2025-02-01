#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ba_action.py
"""
from typing import Dict
from metagpt.actions import Action

BUSINESS_ANALYSIS_PROMPT = """
你是一位业务分析师,请对需求进行业务分析。分析内容需要包含:

1. 业务背景分析
   - 行业现状
   - 业务痛点
   - 市场机会

2. 业务流程分析
   - 现有流程
   - 优化建议
   - 目标流程(使用mermaid flowchart)

3. 组织结构分析
   - 相关方分析
   - 职责划分
   - 协作模式

4. 业务规则分析
   - 业务约束
   - 业务规则
   - 异常处理

需求信息:
{requirements}

请进行分析并返回JSON格式的分析结果。对于流程图使用mermaid语法描述。
"""

BUSINESS_REPORT_PROMPT = """
你是一位业务分析师,请根据业务分析结果编写业务分析报告。报告需要包含:

1. 摘要
   - 项目概述
   - 分析目标
   - 主要发现

2. 业务现状
   - 行业分析
   - 竞争分析
   - 内部分析

3. 问题与机会
   - 业务痛点
   - 改进机会
   - 收益分析

4. 解决方案
   - 业务架构
   - 流程优化
   - 实施建议

5. 结论与建议
   - 主要结论
   - 实施建议
   - 风险提示

业务分析结果:
{analysis}

请编写业务分析报告并以JSON格式返回。对于流程图和架构图使用mermaid语法描述。
"""

class AnalyzeBusiness(Action):
    """进行业务分析"""
    
    async def run(self, requirements: Dict) -> Dict:
        prompt = BUSINESS_ANALYSIS_PROMPT.format(requirements=requirements)
        analysis = await self.llm.aask(prompt)
        return analysis

class WriteBusinessReport(Action):
    """编写业务分析报告"""
    
    async def run(self, analysis: Dict) -> Dict:
        prompt = BUSINESS_REPORT_PROMPT.format(analysis=analysis)
        report = await self.llm.aask(prompt)
        return report 