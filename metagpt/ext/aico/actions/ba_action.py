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
from openpyxl import load_workbook, Workbook
from metagpt.actions import Action
import json
from ..actions.base_action import AICOBaseAction
from pathlib import Path
from metagpt.ext.aico.services import SpecService

# 新增常量
ARCH_REFERENCE_PATH = Path("docs/aico/specs/EA-Design.md")

PARSE_BIZ_REQUIREMENT_PROMPT = """
请按以下优先级应用规范：
1️⃣ 项目专属规范（下方第二部分）
2️⃣ 全局通用规范（下方第一部分）

【全局规范】
{global_spec}

【项目规范】
{project_spec}

请根据以上规范处理需求：
{raw_requirement}
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
        
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 初始化规范服务
        spec_service = SpecService(input_data.get("project_root"))
        
        # 分别获取规范内容
        global_spec = spec_service.get_global_spec("ea_design")
        project_spec = spec_service.get_project_spec("ea_design")
        
        # 生成提示词时分别传递
        prompt = PARSE_BIZ_REQUIREMENT_PROMPT.format(
            global_spec=global_spec,
            project_spec=project_spec,
            raw_requirement=input_data["raw_requirement"]
        )
        result = await self.llm.aask(prompt)
        
        # 写入需求跟踪表
        tracking_file = Path(input_data["tracking_file"])
        if tracking_file.exists():
            wb = load_workbook(tracking_file)
            req_sheet = wb["需求管理"]
        else:
            wb = Workbook()
            # 初始化所有Sheet
            req_sheet = wb.active
            req_sheet.title = "原始需求"
            wb.create_sheet("需求管理")
            wb.create_sheet("用户故事管理")
            wb.create_sheet("任务跟踪")
        
        # 生成需求ID
        req_id = f"REQ-{len(req_sheet.rows):03d}"
        req_data = json.loads(result)
        
        # 写入需求管理表
        req_sheet.append([
            req_id,
            input_data["raw_requirement"],  # 新增原始需求文件
            req_data["business_architecture"]["processes"][0] + "需求",
            req_data["business_architecture"]["processes"][0] + "流程需求",
            "业务需求",
            "高",
            "待评审",
            "BA系统",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "符合业务架构规范",
            "自动生成"
        ])
        
        # 更新原始需求表的关联
        raw_sheet = wb["原始需求"]
        for row in raw_sheet.iter_rows(min_row=2):
            if row[0].value == input_data["raw_requirement"]:
                row[4].value = req_id  # 第5列为关联需求ID
                break
                
        # 更新原始需求状态
        self._update_raw_req_status(
            tracking_file=Path(input_data["tracking_file"]),
            req_file=Path(input_data["raw_requirement"]),
            status="parsed_by_ba",
            role="BA",
            req_id=req_id  # 传递生成的REQ-ID
        )
        
        wb.save(tracking_file)
        
        return {
            "requirement_id": req_id,
            "business_architecture": req_data["business_architecture"],
            "user_stories": req_data["user_stories"],
            "tracking_file": str(tracking_file)
        }

class Update4ABusiness(AICOBaseAction):
    """调用AI引擎更新业务架构,生成用户故事"""
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 加载参考架构
        with open(ARCH_REFERENCE_PATH, "r") as f:
            arch_ref = f.read()
            
        prompt = UPDATE_4A_BUSINESS_PROMPT.format(
            arch_reference=arch_ref,
            requirement_id=input_data["requirement_id"],
            business_arch=input_data["business_architecture"]
        )
        result = await self.llm.aask(prompt)
        analysis = json.loads(result)
        
        # 写入用户故事
        tracking_file = Path(input_data["tracking_file"])
        wb = load_workbook(tracking_file)
        if "用户故事管理" not in wb.sheetnames:
            wb.create_sheet("用户故事管理")
            story_sheet = wb["用户故事管理"]
            story_sheet.append([
                "用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述",
                "优先级", "状态", "验收标准", "创建时间", "备注"
            ])
        else:
            story_sheet = wb["用户故事管理"]
            
        for idx, story in enumerate(analysis["user_stories"], 1):
            story_id = f"US-{len(story_sheet.rows):03d}"
            story_sheet.append([
                story_id,
                input_data["requirement_id"],
                story["title"],
                story["description"],
                "高",  # 默认优先级
                "待评审",  # 状态
                "\n".join(story["acceptance_criteria"]),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "自动生成"
            ])
            
        wb.save(tracking_file)
        
        return {
            "updated_architecture": analysis["business_architecture"],
            "user_stories": analysis["user_stories"],
            "tracking_file": str(tracking_file)
        } 