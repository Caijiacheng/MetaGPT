#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ea_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  EA角色的核心动作包括:
  1. parseTechRequirements: 调用AI引擎分析技术需求,生成需求矩阵
  2. update4ATech: 调用AI引擎更新4A架构(应用架构、数据架构、技术架构)
"""
from typing import Dict
from datetime import datetime
from openpyxl import load_workbook
from metagpt.actions import Action
import json

PARSE_TECH_REQUIREMENT_PROMPT = """
你是一位企业架构师,请调用AI引擎对以下架构文档进行分析,提取技术需求并输出需求矩阵,要求包含:
{
    "requirement_id": "TREQ-XXX",
    "type": "技术需求",
    "title": "需求标题",
    "description": "需求描述",
    "priority": "高/中/低",
    "status": "新建/分析中/已完成",
    "stakeholders": ["相关干系人"],
    "technical_value": "技术价值说明",
    "constraints": "约束条件",
    "dependencies": ["依赖的其他需求ID"],
    "created_time": "YYYY-MM-DD HH:mm:ss"
}

架构文档:
{requirements}
"""

UPDATE_4A_TECH_PROMPT = """
你是一位企业架构师,请基于技术需求矩阵,调用AI引擎协助更新4A架构:

{
    "4a_architecture": {
        "application_architecture": {
            "overview": "应用架构概述",
            "modules": ["功能模块列表"],
            "interfaces": "接口设计",
            "deployment": "部署策略"
        },
        "data_architecture": {
            "data_model": "mermaid语法的ER图",
            "data_flow": "数据流说明",
            "data_governance": "数据治理策略"
        },
        "technical_architecture": {
            "infrastructure": "基础设施",
            "tech_stack": "技术栈选型",
            "security": "安全架构",
            "scalability": "扩展性设计"
        }
    }
}

技术需求矩阵:
{requirement_matrix}
"""

class ParseTechRequirements(Action):
    """调用AI引擎分析技术需求,生成需求矩阵"""
    async def run(self, requirements_info: Dict) -> Dict:
        # 调用AI引擎分析需求
        prompt = PARSE_TECH_REQUIREMENT_PROMPT.format(
            requirements=requirements_info.get("requirements", "")
        )
        requirement_matrix = await self.llm.aask(prompt)
        
        # 写入需求跟踪表
        tracking_file = requirements_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["需求管理"]
            
            # 解析需求矩阵并写入Excel
            matrix_data = json.loads(requirement_matrix)
            row = [
                matrix_data["requirement_id"],
                matrix_data["title"],
                matrix_data["description"],
                "技术需求",  # 需求来源
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

class Update4ATech(Action):
    """调用AI引擎更新4A架构"""
    async def run(self, requirement_info: Dict) -> Dict:
        # 调用AI引擎更新4A架构
        prompt = UPDATE_4A_TECH_PROMPT.format(
            requirement_matrix=requirement_info.get("requirement_matrix", "")
        )
        architecture_result = await self.llm.aask(prompt)
        
        # 写入架构设计文档
        tracking_file = requirement_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["架构设计"]
            # 写入架构设计
            # ws.append([...])  # 具体实现略
            wb.save(tracking_file)
            
        return {
            "4a_architecture": architecture_result.get("4a_architecture"),
            "tracking_file": tracking_file
        } 