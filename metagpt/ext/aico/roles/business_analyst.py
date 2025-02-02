#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : business_analyst.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  业务分析师(BA)角色职责:
  1. 接收并分析业务原始需求(可以是访谈材料、视频、录音等)
  2. 调用AI引擎生成业务需求矩阵
  3. 调用AI引擎更新业务架构和用户故事
  4. 发布分析结果到环境中
"""
import json
from typing import Dict
from .base_role import AICOBaseRole
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ba_action import ParseBizRequirement, Update4ABusiness

class AICOBusinessAnalyst(AICOBaseRole):
    """业务分析师角色"""
    
    name: str = "Alice"
    profile: str = "Business Analyst"
    goal: str = "分析业务需求并生成用户故事"
    constraints: str = "遵循AICO业务需求规范"
    
    def get_actions(self) -> list:
        return [
            ("parse_biz_requirement", ParseBizRequirement),
            ("update_4a_business", Update4ABusiness)
        ]
        
    async def _act(self) -> None:
        # 1. 观察是否有新的项目信息
        project_info = await self.observe(AICOEnvironment.MSG_PROJECT_INFO)
        if not project_info:
            return
            
        # 2. 获取原始需求
        raw_requirements = await self.observe(AICOEnvironment.MSG_RAW_REQUIREMENTS)
        if not raw_requirements:
            return
            
        # 3. 处理原始需求
        raw_req = raw_requirements[-1]
        try:
            req_data = json.loads(raw_req)
            if isinstance(req_data, dict) and "business_demand" in req_data:
                parsed_req = req_data["business_demand"]
                if isinstance(parsed_req, dict):
                    business_req_text = ""
                    for key, value in parsed_req.items():
                        business_req_text += f"{key}: {value}\n"
                    req_text = business_req_text
                else:
                    req_text = str(parsed_req)
            else:
                req_text = raw_req
        except Exception:
            req_text = raw_req
            
        # 4. 调用AI引擎分析需求
        requirements_info = {
            "requirements": req_text,
            "tracking_file": "ReqTracking.xlsx"  # 可配置
        }
        
        # 5. 生成需求矩阵
        parse_action = self.get_action("parse_biz_requirement")
        requirement_matrix = await parse_action.run(requirements_info)
        # 6. 发布需求矩阵
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_MATRIX, requirement_matrix)
        
        # 7. 更新业务架构和用户故事
        update_action = self.get_action("update_4a_business")
        analysis_result = await update_action.run(requirement_matrix)
        # 8. 发布分析结果
        await self.publish(AICOEnvironment.MSG_BUSINESS_ARCHITECTURE, 
                         analysis_result.get("business_architecture"))
        await self.publish(AICOEnvironment.MSG_USER_STORIES, 
                         analysis_result.get("user_stories")) 