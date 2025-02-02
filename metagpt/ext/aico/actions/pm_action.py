#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : pm_action.py
说明:
  PM角色的核心动作包括:
  1. PrepareProject: 初始化项目,生成项目基本信息
  2. ReviewAllRequirements: 调用AI引擎复核需求,形成需求基线
  3. PlanSprintReleases: 调用AI引擎制定迭代计划
  4. ReviewAllDesigns: 调用AI引擎复核设计文档
  5. ReviewAllTasks: 调用AI引擎复核任务分解
"""
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from openpyxl import Workbook, load_workbook
import logging
import shutil
from metagpt.actions import Action
import json
from metagpt.ext.aico.services.spec_service import SpecService
import os

REVIEW_REQUIREMENTS_PROMPT = """作为资深项目经理，请根据以下材料进行需求复核：

【原始需求】
{raw_requirement}

【已解析需求】
{parsed_requirements}

【关联文档】
用户故事: {user_stories}
业务架构: {business_arch}
技术架构: {tech_arch}

请检查：
1. 存在的需求类型（业务/技术）是否解析完整
2. 需求与架构设计是否一致
3. 用户故事是否可追溯至需求（如存在业务需求）
4. 是否存在矛盾或缺失

输出格式：
{{
    "approved": true/false,
    "missing_items": ["缺失项列表"],
    "conflicts": ["矛盾点列表"],
    "trace_issues": ["可追溯性问题"],
    "suggestions": "改进建议"
}}"""

PLAN_SPRINT_PROMPT = """
你是一位项目经理,请调用AI引擎基于以下需求制定迭代计划,输出JSON格式:
{
    "sprint_plan": {
        "total_sprints": "迭代总数",
        "sprint_duration": "每个迭代的周期(周)",
        "sprints": [
            {
                "sprint_id": "迭代编号",
                "start_date": "开始日期",
                "end_date": "结束日期",
                "goals": ["目标1", "目标2"],
                "user_stories": ["故事1", "故事2"],
                "estimated_story_points": "预估故事点",
                "key_results": ["关键结果1", "关键结果2"]
            }
        ]
    }
}

需求和用户故事:
{requirements_and_stories}
"""

REVIEW_DESIGNS_PROMPT = """
你是一位项目经理,请调用AI引擎对以下设计文档进行复核,输出JSON格式的复核结果:
{
    "design_review": {
        "architecture_review": {
            "completeness": "完整度评分",
            "consistency": "一致性评分",
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1", "建议2"]
        },
        "interface_review": {
            "clarity": "清晰度评分",
            "standards": "规范性评分",
            "issues": ["问题1", "问题2"]
        },
        "data_model_review": {
            "rationality": "合理性评分",
            "issues": ["问题1", "问题2"]
        },
        "overall_assessment": "总体评估",
        "review_time": "YYYY-MM-DD HH:mm:ss"
    }
}

设计文档:
{designs}
"""

REVIEW_TASKS_PROMPT = """
你是一位项目经理,请调用AI引擎对以下任务分解进行复核,输出JSON格式的复核结果:
{
    "task_review": {
        "completeness": "是否覆盖所有需求",
        "granularity": "任务粒度是否合适",
        "dependencies": "任务依赖关系是否合理",
        "workload": "工作量是否合理",
        "issues": ["问题1", "问题2"],
        "suggestions": ["建议1", "建议2"],
        "review_time": "YYYY-MM-DD HH:mm:ss"
    }
}

任务列表:
{tasks}
"""

class ParseSpecStructure(AICOBaseAction):
    """解析规范文档结构"""
    
    async def _run_impl(self, input_data: Dict) -> Dict:
        spec_service = SpecService(input_data.get("project_root"))
        spec_content = spec_service.get_global_spec("project_tracking")
        
        prompt = f"""
        请从以下规范文档中解析出Excel跟踪表的结构要求：
        {spec_content}
        
        输出JSON格式：
        {{
            "sheets": {{
                "表名": ["字段1", "字段2..."]
            }},
            "file_naming": "文件命名规则说明",
            "path_rules": "路径存储规则"
        }}
        """
        result = await self.llm.aask(prompt)
        return json.loads(result)

class PrepareProject(AICOBaseAction):
    """初始化项目"""
    def __init__(self):
        super().__init__()


    async def run(self, project_info: Dict) -> Dict:
        """初始化或更新项目
        
        Args:
            project_info: 项目信息
                - name: 项目名称
                - output_root: 输出根目录
                - raw_requirement: 原始需求(文件路径或文本)
                - iteration: 当前迭代次数(默认为1)
        """
        # 
        pass

    async def _run_impl(self, input_data: Dict) -> Dict:
        # 初始化规范服务
        spec_service = SpecService(input_data["project_root"])
        
        # 1. 解析规范结构
        parse_action = self.get_action("parse_spec_structure")
        spec_structure = await parse_action.run({
            "project_root": input_data["project_root"]
        })
        
        # 2. 创建跟踪文件
        tracking_file = Path(os.getenv("TRACKING_FILE", "tracking/ReqTracking.xlsx"))
        self._create_tracking_file(tracking_file, spec_structure["sheets"])
        
        # 3. 初始化项目规范
        for spec_type in ["ea_design", "project_tracking"]:
            spec_service.init_project_spec(spec_type)
            
        return {
            "project_root": input_data["project_root"],
            "tracking_file": str(tracking_file),
            "spec_structure": spec_structure
        }

    def _create_tracking_file(self, file_path: Path, sheets_config: Dict):
        wb = Workbook()
        for sheet_name, headers in sheets_config.items():
            ws = wb.create_sheet(sheet_name)
            ws.append(headers)
        wb.save(file_path)

class ReviewAllRequirements(Action):
    """复核需求"""
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 从输入数据中提取各类文档
        raw_req = input_data.get("raw_requirement", "")
        parsed_req = input_data.get("parsed_requirements", {})
        user_stories = input_data.get("user_stories", "")
        business_arch = input_data.get("business_arch", "")
        tech_arch = input_data.get("tech_arch", "")
        
        prompt = REVIEW_REQUIREMENTS_PROMPT.format(
            raw_requirement=raw_req,
            parsed_requirements=json.dumps(parsed_req, indent=2),
            user_stories=user_stories,
            business_arch=business_arch,
            tech_arch=tech_arch
        )
        
        result = await self.llm.aask(prompt)
        return self._parse_result(result)
        
    def _parse_result(self, raw: str) -> Dict:
        try:
            data = json.loads(raw)
            return {
                "approved": data.get("approved", False),
                "issues": {
                    "missing": data.get("missing_items", []),
                    "conflicts": data.get("conflicts", []),
                    "traceability": data.get("trace_issues", [])
                },
                "suggestions": data.get("suggestions", "")
            }
        except Exception as e:
            return {
                "approved": False,
                "issues": {"parse_error": [f"JSON解析失败: {str(e)}"]},
                "suggestions": "请检查AI输出格式"
            }

class PlanSprintReleases(Action):
    """制定迭代计划"""
    async def run(self, requirements_and_stories: Dict) -> Dict:
        # 调用AI引擎制定迭代计划
        prompt = PLAN_SPRINT_PROMPT.format(
            requirements_and_stories=requirements_and_stories
        )
        sprint_plan = await self.llm.aask(prompt)
        return sprint_plan

class ReviewAllDesigns(Action):
    """复核设计文档"""
    async def run(self, designs: Dict) -> Dict:
        # 调用AI引擎复核设计
        prompt = REVIEW_DESIGNS_PROMPT.format(
            designs=designs
        )
        review_result = await self.llm.aask(prompt)
        return review_result

class ReviewAllTasks(Action):
    """复核任务分解"""
    async def run(self, tasks: Dict) -> Dict:
        # 调用AI引擎复核任务
        prompt = REVIEW_TASKS_PROMPT.format(
            tasks=tasks
        )
        review_result = await self.llm.aask(prompt)
        return review_result 