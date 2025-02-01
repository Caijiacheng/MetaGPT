#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : enterprise_architect.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  企业架构师(EA)角色职责:
  1. 接收并分析技术需求(从架构文档中提取)
  2. 调用AI引擎生成技术需求矩阵
  3. 调用AI引擎更新4A架构(应用架构、数据架构、技术架构)
  4. 发布分析结果到环境中
"""
from typing import Dict
import json
from .base_role import AICOBaseRole
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ea_action import ParseTechRequirements, Update4ATech

class AICOEnterpriseArchitect(AICOBaseRole):
    """企业架构师角色"""
    
    name: str = "Bob"
    profile: str = "Enterprise Architect"
    goal: str = "分析技术需求并设计系统架构"
    constraints: str = "遵循AICO技术架构规范"
    
    def get_actions(self) -> list:
        return [
            ("parse_tech_requirements", ParseTechRequirements),
            ("update_4a_tech", Update4ATech)
        ]
        
    async def _act(self):
        parse_action = self.get_action("parse_tech_requirements")
        # 1. 观察是否有新的项目信息
        project_info = await self.observe(AICOEnvironment.MSG_PROJECT_INFO)
        if not project_info:
            return
            
        # 2. 获取架构文档
        arch_docs = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
        if not arch_docs:
            return
            
        # 3. 处理架构文档
        arch_doc = arch_docs[-1]
        try:
            req_data = json.loads(arch_doc)
            if isinstance(req_data, dict) and "technical_demand" in req_data:
                tech_req = req_data["technical_demand"]
                if isinstance(tech_req, dict):
                    tech_req_text = ""
                    for key, value in tech_req.items():
                        tech_req_text += f"{key}: {value}\n"
                    req_text = tech_req_text
                else:
                    req_text = str(tech_req)
            else:
                req_text = arch_doc
        except Exception:
            req_text = arch_doc
            
        # 4. 调用AI引擎分析需求
        requirements_info = {
            "requirements": req_text,
            "tracking_file": "ReqTracking.xlsx"  # 可配置
        }
        
        # 5. 生成技术需求矩阵
        requirement_matrix = await parse_action.run(requirements_info)
        # 6. 发布需求矩阵
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_MATRIX, requirement_matrix)
        
        # 7. 更新4A架构
        update_action = self.get_action("update_4a_tech")
        architecture_result = await update_action.run(requirement_matrix)
        # 8. 发布架构设计
        await self.publish(AICOEnvironment.MSG_4A_ASSESSMENT, 
                         architecture_result.get("4a_architecture"))
