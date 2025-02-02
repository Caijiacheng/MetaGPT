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

class PrepareProject(Action):
    """初始化AICO项目结构
    TODO: 需要补充SpecService具体实现
    生成目录结构：
    ├── docs/
    │   ├── aico/specs/          # 规范文档
    │   ├── ea/                 # 4A架构文档
    │   └── requirements/       # 需求文档
    ├── tracking/
    │   └── ProjectTracking.xlsx # 项目跟踪表
    ├── src/                    # 源代码
    └── config/                 # 配置文件
    """
    
    async def run(self, project_root: str) -> Dict:
        """创建基础项目结构"""
        project_path = Path(project_root)
        dirs = [
            "docs/aico/specs",
            "docs/ea",
            "docs/requirements",
            "tracking",
            "src",
            "config"
        ]
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)

        # 初始化跟踪文件（根据project_tracking_spec.md规范）
        tracking_file = project_path / "tracking/ProjectTracking.xlsx"
        wb = Workbook()
        sheets = {
            "原始需求": ["需求文件", "需求类型", "添加时间", "当前状态", "关联需求ID",
                      "BA解析时间", "EA解析时间", "完成时间", "备注"],
            "需求管理": ["需求ID", "原始需求文件", "需求名称", "需求描述", "需求来源",
                      "需求优先级", "需求状态", "提出人/负责人", "提出时间", "目标完成时间",
                      "验收标准", "备注"],
            "用户故事管理": ["用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述",
                         "优先级", "状态", "验收标准", "创建时间", "备注"],
            "任务跟踪": ["任务ID", "关联需求ID", "关联用户故事ID", "任务名称", "任务描述",
                      "任务类型", "负责人", "任务状态", "计划开始时间", "计划结束时间",
                      "实际开始时间", "实际结束时间", "备注"]
        }
        
        for sheet_name, headers in sheets.items():
            wb.create_sheet(sheet_name)
            wb[sheet_name].append(headers)
        
        wb.save(tracking_file)
        
        return {
            "project_root": str(project_root),
            "tracking_file": str(tracking_file),
            "specs": ["ea_design", "project_tracking"]  # TODO: 需要接入SpecService
        }

class ReviewAllRequirements(Action):
    """复核所有已分析需求（根据文档6.1.3节）"""
    
    async def run(self, requirements: dict):
        # 实现需求一致性检查逻辑
        # 返回结构示例:
        # {
        #   "consistency": True,
        #   "conflicts": [],
        #   "suggestions": "需求基线已就绪"
        # }
        return ActionOutput(
            instruct_content=await self._check_consistency(requirements),
            content=requirements
        )
    
    async def _check_consistency(self, reqs: dict) -> dict:
        # 实现具体的检查逻辑...
        pass

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