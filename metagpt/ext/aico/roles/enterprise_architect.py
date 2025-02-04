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
from openpyxl import load_workbook
from datetime import datetime
from pathlib import Path

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
        # 接收分析任务（依赖BA输出）
        msg = await self.observe(AICOEnvironment.MSG_REQUIREMENT_TECH_ANALYSIS)
        req_file = Path(msg.content["file_path"])
        
        # 执行分析...
        tech_arch = await self._analyze_tech(msg.content["business_arch"])
        
        
        # 发布技术架构
        await self.publish(AICOEnvironment.MSG_TECH_ARCH, {
            "req_id": msg.content["req_id"],
            "architecture": tech_arch
        })
        
        # 发布分析完成通知
        await self.publish(AICOEnvironment.MSG_EA_ANALYSIS_DONE, {
            "req_id": req_file.stem,
            "output_files": [
                str(req_file),
                str(tech_arch)
            ],
            "status": "completed"
        })

    def _update_req_status(self, tracking_file: Path, status: str, req_id: str):
        """更新需求跟踪表状态"""
        wb = load_workbook(tracking_file)
        ws = wb["需求管理"]
        
        for row in ws.iter_rows(min_row=2):
            if row[0].value == req_id:  # 需求ID列
                row[3].value = status  # 状态列
                row[5].value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # EA解析时间
                break
            
        wb.save(tracking_file)
