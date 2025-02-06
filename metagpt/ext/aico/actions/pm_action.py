#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : pm_action.py
说明:
  PM角色的核心动作包括:
  1. ReviewAllRequirements: 调用AI引擎复核需求,形成需求基线
  2. TODO: ReviewAllDesigns: 调用AI引擎复核设计文档,形成设计基线
  3. TODO: ReviewAllImpTasks: 调用AI引擎复核需求实现,形成实现基线
  4. TODO: ReviewChanges: 调用AI引擎复核整个项目的changlog，形成版本
"""
from typing import Dict
from metagpt.actions import Action
import json

from metagpt.actions.action_output import ActionOutput


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





class ReviewAllRequirements(Action):
    """复合需求检查（严格遵循文档6.1.3节要求）"""
    
    async def run(self, context: dict):
        # AI预审结果
        ai_result = await self._ai_review(context)
        
        # 返回包含人工审核字段的结果
        return ActionOutput(
            content={
                "ai_approved_reqs": ai_result["approved"],
                "ai_rejected_reqs": ai_result["rejected"],
                "human_confirmed": False  # 初始未确认
            },
            instruct_content={
                "need_human_review": True,
                "review_summary": "请人工复核以下需求..."
            }
        )

    async def _check_biz_tech_alignment(self, data: dict) -> dict:
        """业务需求与技术需求对齐检查（文档6.1.3节第1点）"""
        biz_reqs = data.get("business_requirements", [])
        tech_reqs = data.get("technical_requirements", [])
        
        missing_tech = [req for req in biz_reqs if not any(t['biz_id'] == req['id'] for t in tech_reqs)]
        missing_biz = [req for req in tech_reqs if not any(b['id'] == req['biz_id'] for b in biz_reqs)]
        
        return {
            "missing_technical": missing_tech,
            "missing_business": missing_biz,
            "conflicts": await self._find_conflicts(biz_reqs, tech_reqs)
        }

    async def _check_story_coverage(self, data: dict) -> dict:
        """用户故事覆盖检查（文档6.1.3节第2点）"""
        biz_reqs = data.get("business_requirements", [])
        stories = data.get("user_stories", [])
        
        uncovered = []
        for req in biz_reqs:
            if not any(story['req_id'] == req['id'] for story in stories):
                uncovered.append(req['id'])
        
        return {
            "uncovered_requirements": uncovered,
            "invalid_stories": [s for s in stories if s.get('status') not in ('TODO', 'IN_PROGRESS', 'DONE')]
        }

    async def _check_traceability(self, data: dict) -> dict:
        """需求可追溯性检查（文档6.1.3节第3点）"""
        trace_issues = []
        # 检查需求->用户故事->任务的追溯链
        for req in data.get("business_requirements", []):
            if not any(story['req_id'] == req['id'] for story in data.get("user_stories", [])):
                trace_issues.append(f"需求 {req['id']} 缺少关联用户故事")
                
        # 检查技术需求->任务的追溯
        for tech in data.get("technical_requirements", []):
            if not any(task['tech_id'] == tech['id'] for task in data.get("tasks", [])):
                trace_issues.append(f"技术需求 {tech['id']} 缺少关联任务")
        
        return {"trace_issues": trace_issues}


class ReviewAllDesigns(Action):
    """TODO: 复核设计文档"""
    async def run(self, designs: Dict) -> Dict:
        raise NotImplementedError("设计复核功能待实现")

class ReviewAllTasks(Action):
    """TODO: 复核任务分解"""
    async def run(self, tasks: Dict) -> Dict:
        raise NotImplementedError("任务复核功能待实现")

class ReviewChanges(Action):
    """TODO: 变更复核"""
    async def run(self, change_log: Dict) -> Dict:
        raise NotImplementedError("变更复核功能待实现")

class ReviewDesign(Action):
    """设计文档复核（文档6.2节）"""
    
    async def run(self, design_doc: str) -> ActionOutput:
        """执行设计文档复核"""
        # 实现设计文档的自动校验逻辑
        # 示例：检查是否符合架构规范
        spec = self.role.get_spec("ea_design")
        result = await self._aico_validate(design_doc, spec)
        
        return ActionOutput(
            content=result,
            instruct_content={
                "approval": result["is_valid"],
                "comments": result["errors"]
            }
        ) 