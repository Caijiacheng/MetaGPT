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
from typing import Dict, List
from datetime import datetime
from openpyxl import load_workbook, Workbook
from metagpt.actions import Action
import json

from pathlib import Path
from metagpt.ext.aico.services import DocManagerService, DocType
from metagpt.actions import ActionOutput
import logging

# 新增常量
ARCH_REFERENCE_PATH = Path("docs/aico/specs/EA-Design.md")

PARSE_BIZ_REQUIREMENT_PROMPT = """
作为资深业务分析师，请根据以下规范分析需求：

【优先应用规范】
{project_spec}

【全局参考规范】
{global_spec}

【待分析需求内容】
{raw_requirement}

请按以下结构输出：
1. 业务架构更新建议
2. 关键业务流程（Mermaid图表）
3. 初步用户故事列表
"""

UPDATE_4A_BUSINESS_PROMPT = """
基于当前架构：
{current_architecture}

和需求矩阵：
{requirement_matrix}

请：
1. 更新4A业务架构
2. 生成符合INVEST原则的用户故事
3. 标识与之前版本的变更点
"""

logger = logging.getLogger(__name__)

class ParseBizRequirement(Action):
    """遵循规范的业务需求解析"""
    
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 使用文档服务获取规范
        doc_manager = DocManagerService(Path(input_data["project_root"]))
        
        # 生成带规范优先级的提示词
        project_spec = doc_manager.get_spec(DocType.SPEC_EA)
        global_spec = doc_manager.get_spec(DocType.SPEC_EA, use_project=False)
        
        prompt = PARSE_BIZ_REQUIREMENT_PROMPT.format(
            global_spec=global_spec,
            project_spec=project_spec,
            raw_requirement=input_data["raw_requirement"]
        )
        
        # 调用LLM并解析结果
        result = await self.parse_llm_response(prompt)
        
        # 使用文档服务生成标准ID
        doc_manager = DocManagerService(Path(input_data["project_root"]))
        req_id = doc_manager.generate_doc_id(
            DocType.REQUIREMENT_ANALYZED,
            prefix="RQ-B"
        )
        
        return ActionOutput(
            content=input_data,
            instruct_content={
                "requirement_id": req_id,
                "standard_requirements": [
                    {
                        "std_req_id": f"SR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "description": req_desc,
                        "priority": "高"
                    }
                    for req_desc in result["requirements"]
                ]
            }
        )

    async def parse_llm_response(self, prompt: str) -> dict:
        """标准化响应解析（新增规范校验）"""
        raw_result = await self.llm.aask(prompt)
        try:
            result = json.loads(raw_result)
            # 校验必要字段
            assert "business_architecture" in result
            assert "process_diagram" in result
            assert "user_stories" in result
            return result
        except (json.JSONDecodeError, AssertionError) as e:
            logger.error(f"LLM响应解析失败: {str(e)}")
            raise ValueError("业务需求解析结果格式错误")

class Update4ABusiness(Action):
    """基于规范更新4A业务架构"""
    
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 加载当前业务架构
        arch_file = Path(input_data["project_root"]) / "docs/ea/biz_architecture.md"
        current_arch = arch_file.read_text(encoding="utf-8") if arch_file.exists() else ""
        
        # 生成更新提示词
        prompt = UPDATE_4A_BUSINESS_PROMPT.format(
            current_architecture=current_arch,
            requirement_matrix=json.dumps(input_data["requirement_matrix"], indent=2)
        )
        
        # 调用LLM生成更新建议
        result = await self.parse_llm_response(prompt)
        
        # 保存更新后的架构
        arch_file.parent.mkdir(parents=True, exist_ok=True)
        arch_file.write_text(result["updated_architecture"], encoding="utf-8")
        
        # 新增架构变更对比
        old_arch = input_data.get("current_architecture", "")
        new_arch = result["updated_architecture"]
        changes = self._diff_architecture(old_arch, new_arch)
        
        return ActionOutput(
            content=input_data,
            instruct_content={
                "user_stories": {
                    std_req["std_req_id"]: [
                        {
                            "story_id": f"US-{std_req['std_req_id']}-{idx:02d}",
                            "title": story["title"],
                            "status": "待评审",
                            "acceptance_criteria": story["acceptance_criteria"]
                        }
                        for idx, story in enumerate(result["user_stories"].get(std_req["std_req_id"], []), 1)
                    ]
                    for std_req in input_data["standard_requirements"]
                },
                "version": datetime.now().strftime("%Y%m%d%H%M")
            }
        )
    
    def _format_user_stories(self, stories: List, req_id: str) -> List:
        return [{
            **story,
            "req_id": req_id,
            "status": "待评审",
            "created_time": datetime.now().isoformat()
        } for story in stories] 