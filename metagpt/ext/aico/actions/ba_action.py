#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : ba_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  BA角色的核心动作包括:
  1. parseBizRequirement: 调用AI引擎分析业务需求,生成需求矩阵
  2. update4ABusiness: 调用AI引擎更新业务架构,生成用户故事
"""
from typing import Dict
from datetime import datetime
from openpyxl import load_workbook
from metagpt.actions import Action
import json
from ..actions.base_action import AICOBaseAction

PARSE_BIZ_REQUIREMENT_PROMPT = """
你是一位业务分析师,请调用AI引擎对以下业务需求文本进行分析,输出业务需求矩阵,要求包含:
{
    "requirement_id": "REQ-XXX",
    "type": "业务需求",
    "title": "需求标题",
    "description": "需求描述",
    "priority": "高/中/低",
    "status": "新建/分析中/已完成",
    "stakeholders": ["相关干系人"],
    "business_value": "业务价值说明",
    "constraints": "约束条件",
    "dependencies": ["依赖的其他需求ID"],
    "created_time": "YYYY-MM-DD HH:mm:ss"
}

原始需求信息:
{requirements}
"""

UPDATE_4A_BUSINESS_PROMPT = """
你是一位业务分析师,请基于业务需求矩阵,调用AI引擎协助更新业务架构并生成用户故事:

1. 业务架构部分需包含:
{
    "business_architecture": {
        "vision": "企业愿景",
        "goals": ["业务目标"],
        "scope": "业务范围",
        "capabilities": ["核心能力", "支撑能力"],
        "process": {
            "diagram": "mermaid语法的业务流程图",
            "description": "流程说明"
        }
    }
}

2. 用户故事部分需包含:
{
    "story_id": "US-XXX",
    "related_req_id": "REQ-XXX",
    "title": "故事名称",
    "description": "As a <角色>, I want <功能> so that <价值>",
    "priority": "高/中/低",
    "status": "待评审",
    "acceptance_criteria": "验收标准",
    "created_time": "YYYY-MM-DD HH:mm:ss"
}

业务需求矩阵:
{requirement_matrix}
"""

class ParseBizRequirement(AICOBaseAction):
    """调用AI引擎分析业务需求"""
    
    async def validate_input(self, input_data: Dict) -> bool:
        required_fields = ["raw_requirement", "tracking_file"]
        return all(field in input_data for field in required_fields)
        
    async def run(self, input_data: Dict) -> Dict:
        if not await self.validate_input(input_data):
            raise ValueError("缺少必要输入字段")
            
        # 调用AI引擎分析需求
        prompt = PARSE_BIZ_REQUIREMENT_PROMPT.format(
            requirements=input_data["raw_requirement"]
        )
        requirement_matrix = await self.llm.aask(prompt)
        
        # 写入需求跟踪表
        tracking_file = input_data["tracking_file"]
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["需求管理"]
            
            # 解析需求矩阵并写入Excel
            matrix_data = json.loads(requirement_matrix)
            row = [
                matrix_data["requirement_id"],
                matrix_data["title"],
                matrix_data["description"],
                "业务需求",  # 需求来源
                matrix_data["priority"],
                matrix_data["status"],
                matrix_data["stakeholders"][0],  # 提出人取第一个干系人
                matrix_data["created_time"],
                "",  # 目标完成时间待定
                matrix_data.get("acceptance_criteria", ""),
                matrix_data.get("constraints", "")  # 约束作为备注
            ]
            ws.append(row)
            wb.save(tracking_file)
            
        return {
            "requirement_matrix": requirement_matrix,
            "tracking_file": tracking_file
        }

class Update4ABusiness(Action):
    """调用AI引擎更新业务架构,生成用户故事"""
    async def run(self, requirement_info: Dict) -> Dict:
        # 调用AI引擎生成业务架构和用户故事
        prompt = UPDATE_4A_BUSINESS_PROMPT.format(
            requirement_matrix=requirement_info.get("requirement_matrix", "")
        )
        analysis_result = await self.llm.aask(prompt)
        
        # 写入用户故事到跟踪表
        tracking_file = requirement_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["用户故事"]
            # 写入用户故事
            # ws.append([...])  # 具体实现略
            wb.save(tracking_file)
            
        return {
            "business_architecture": analysis_result.get("business_architecture"),
            "user_stories": analysis_result.get("user_stories"),
            "tracking_file": tracking_file
        } 