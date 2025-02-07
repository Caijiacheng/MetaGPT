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
from typing import Dict, List
from datetime import datetime
from openpyxl import load_workbook
from metagpt.actions import Action, ActionOutput
import json
from pathlib import Path
from metagpt.ext.aico.services.doc_manager import DocManagerService, DocType
import asyncio

PARSE_TECH_REQUIREMENT_PROMPT = """
根据技术规范分析需求：

【项目规范】
{project_spec}

【全局规范】
{global_spec}

【技术需求内容】
{requirements}

输出要求：
1. 技术需求矩阵（ID/描述/优先级）
2. 架构影响分析
3. 技术约束说明
"""

UPDATE_4A_TECH_PROMPT = """
基于当前架构版本：
{current_architecture}

和需求矩阵：
{requirement_matrix}

请：
1. 更新应用/数据/技术架构
2. 生成架构变更说明
3. 标识技术选型变化
"""

ARCH_REFERENCE_PATH = Path("docs/aico/specs/EA-Design.md")

class ParseTechRequirements(Action):
    """遵循规范的技术需求解析"""
    
    async def _run_impl(self, input_data: Dict) -> Dict:
        doc_manager = DocManagerService(Path(input_data["project_root"]))
        
        # 获取规范内容
        project_spec = doc_manager.get_spec(DocType.SPEC_EA)
        global_spec = doc_manager.get_spec(DocType.SPEC_EA, use_project=False)
        
        prompt = PARSE_TECH_REQUIREMENT_PROMPT.format(
            project_spec=project_spec,
            global_spec=global_spec,
            requirements=input_data["raw_requirement"]
        )
        
        # 调用LLM并解析
        result = await self._parse_llm_response(prompt)
        
        # 生成需求矩阵文档
        matrix_file = doc_manager.save_document(
            doc_type=DocType.TECH_REQUIREMENT,
            content=json.dumps(result, indent=2),
            version=input_data["version"],
            req_id=input_data["req_id"]
        )
        
        return ActionOutput(
            content=input_data,
            instruct_content=result,
            output_file=str(matrix_file)
        )

    async def _parse_llm_response(self, prompt: str) -> Dict:
        """标准化解析LLM响应"""
        max_retries = 3
        backoff_factor = 1.5
        
        for attempt in range(max_retries):
            try:
                raw_result = await self.llm.aask(prompt)
                
                # 提取可能的JSON块
                json_str = raw_result.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_str)
                
                # 校验基础结构
                required_fields = {
                    "ParseTechRequirements": ["requirements", "impact_analysis", "constraints"],
                    "Update4ATech": ["architecture", "components", "dependencies", "change_log"]
                }
                
                action_type = self.__class__.__name__
                for field in required_fields.get(action_type, []):
                    if field not in result:
                        raise ValueError(f"缺少必要字段: {field}")
                
                # 架构专项校验
                if action_type == "Update4ATech":
                    if not isinstance(result["architecture"], dict):
                        raise ValueError("架构信息必须是字典")
                    if "application_architecture" not in result["architecture"]:
                        raise ValueError("缺少应用架构定义")
                        
                return result
                
            except (IndexError, json.JSONDecodeError) as e:
                self.logger.warning(f"JSON解析失败，第{attempt+1}次重试... 错误: {str(e)}")
                prompt += "\n请严格按照JSON格式输出，确保语法正确"
                if attempt == max_retries - 1:
                    self.logger.error("达到最大重试次数，使用降级方案")
                    return self._generate_fallback_output(action_type)
                await asyncio.sleep(backoff_factor ** attempt)
                
            except ValueError as e:
                self.logger.error(f"字段校验失败: {str(e)}")
                prompt += f"\n请确保包含以下字段: {required_fields.get(action_type, '')}"
                if attempt == max_retries - 1:
                    return self._generate_fallback_output(action_type)
                await asyncio.sleep(backoff_factor ** attempt)

    def _generate_fallback_output(self, action_type: str) -> Dict:
        """生成降级输出"""
        fallback_templates = {
            "ParseTechRequirements": {
                "requirements": [],
                "impact_analysis": "架构影响分析失败",
                "constraints": "无法获取技术约束"
            },
            "Update4ATech": {
                "architecture": {
                    "application_architecture": {"services": []},
                    "data_architecture": {"models": []},
                    "technical_architecture": {"components": []}
                },
                "components": [],
                "dependencies": [],
                "change_log": ["生成架构失败，使用默认配置"]
            }
        }
        self.logger.warning(f"使用降级方案 for {action_type}")
        return fallback_templates.get(action_type, {})

class Update4ATech(Action):
    """基于规范更新4A技术架构"""
    
    async def _run_impl(self, input_data: Dict) -> Dict:
        # 生成架构更新提示词
        prompt = UPDATE_4A_TECH_PROMPT.format(
            current_architecture=input_data["current_architecture"],
            requirement_matrix=json.dumps(input_data["requirement_matrix"], indent=2)
        )
        
        # 调用LLM生成架构
        result = await self._parse_llm_response(prompt)
        
        # 生成架构变更说明
        change_log = self._generate_change_log(
            input_data["current_architecture"],
            result["architecture"]
        )
        
        return ActionOutput(
            content=input_data,
            instruct_content={
                "architecture": result["architecture"],
                "components": result.get("components", []),
                "dependencies": result.get("dependencies", []),
                "change_log": change_log
            }
        )
    
    def _generate_change_log(self, old_arch: str, new_arch: str) -> List[str]:
        """生成架构变更日志"""
        # 实现差异对比逻辑...
        return ["架构初始化"] if not old_arch else ["版本更新"]

    def _parse_arch(self, raw: str) -> Dict:
        try:
            data = json.loads(raw)
            # 强制字段检查
            assert "application_architecture" in data
            assert "services" in data["application_architecture"]
            return data
        except (json.JSONDecodeError, AssertionError) as e:
            self.logger.error(f"架构解析失败: {str(e)}")
            return self._generate_fallback_output()
            
    def _generate_fallback_output(self):
        """生成符合规范的空结构"""
        return {
            "application_architecture": {"services": [], "interfaces": []},
            "technical_architecture": {"deployment": "", "infrastructure": []},
            "data_architecture": {"models": [], "data_flow": ""},
            "security_architecture": {"access_control": ""}
        }
