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
from pathlib import Path

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
        # 从跟踪表获取待分析需求路径
        tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
        req_path = self._get_pending_requirement(tracking_file)
        
        # 读取需求内容
        content = (self.project_root / req_path).read_text(encoding="utf-8")
        
        # 执行分析...
        analysis_result = await self._analyze_requirement(content)
        
        # 更新跟踪表状态
        self._update_tracking_status(req_path, "ba_parsed_time")
        
        # 发布业务架构
        await self.publish(AICOEnvironment.MSG_BUSINESS_ARCH, {
            "req_id": req_path,
            "architecture": analysis_result
        })
        
        # 发布分析结果
        await self.publish(AICOEnvironment.MSG_USER_STORIES, 
                         analysis_result.get("user_stories"))
        
        # 发布分析完成通知
        await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_DONE, {
            "req_id": req_path.stem,
            "output_files": [
                str(arch_doc_path),
                str(req_matrix_path)
            ],
            "status": "completed"
        }) 