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

from typing import Dict
from metagpt.roles import Role
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.ba_action import ParseBizRequirement, Update4ABusiness
from pathlib import Path
import logging
from datetime import datetime
from metagpt.ext.aico.services.doc_manager import DocManagerService, DocType

logger = logging.getLogger(__name__)

class AICOBusinessAnalyst(Role):
    """遵循AICO规范的业务分析师角色"""
    
    name: str = "AICO_BA"
    profile: str = "Business Analyst"
    goal: str = "解析业务需求并维护业务架构"
    constraints: str = "严格遵循AICO业务需求规范"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ParseBizRequirement, Update4ABusiness])
        self.doc_manager = DocManagerService(self.project_root)
        
    async def _act(self) -> None:
        """纯消息驱动模式"""
        async for msg in self.observe(AICOEnvironment.MSG_REQUIREMENT_BIZ_ANALYSIS.name):
            try:
                # 通知PM分析开始
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_STARTED.name, {
                    "req_id": msg.content["req_id"],
                    "start_time": datetime.now().isoformat()
                })
                
                result = await self._process_requirement(msg.content)
                
                # 生成用户故事文档
                stories_file = self._save_user_stories(result["biz_req_id"], result["version"])
                
                # 返回处理结果给PM
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_DONE.name, {
                    "req_id": msg.content["req_id"],
                    "standard_req": result["standard_req"],
                    "user_stories": result["user_stories"],
                    "output_files": [
                        str(stories_file),
                        result["architecture_file"]
                    ]
                })
                
            except Exception as e:
                logger.error(f"需求分析失败: {msg.content['req_id']}")
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_FAILED.name, {
                    "req_id": msg.content["req_id"],
                    "error": str(e),
                    "fail_time": datetime.now().isoformat()
                })

    def _save_user_stories(self, project_id: str, version: str) -> Path:
        """生成并保存用户故事文档"""
        # 使用文档模板生成内容
        content = self.doc_manager.template.user_story(
            version=version,
            stories=self.user_stories
        )
        
        # 保存文档
        return self.doc_manager.save_document(
            doc_type=DocType.USER_STORY,
            content=content,
            version=version,
            req_id=project_id,
            service_name="product"  # 根据规范参数命名
        )

    async def _process_requirement(self, req_info: dict) -> dict:
        """处理业务需求分析核心逻辑"""
        
        req_file = self.project_root / req_info["file_path"]
        content = req_file.read_text(encoding="utf-8")
        
        # 执行需求解析
        parse_result = await self.rc.run(
            ParseBizRequirement().run({
                "raw_requirement": content,
                "project_root": str(self.project_root),
                "req_id": req_info["req_id"]
            })
        )
        
        # 更新业务架构
        update_result = await self.rc.run(
            Update4ABusiness().run({
                "requirement_matrix": parse_result.instruct_content,
                "project_root": str(self.project_root),
                "req_id": req_info["req_id"]
            })
        )
        
        # 获取业务架构文档路径
        biz_arch_path = self.doc_manager.get_doc_path(
            DocType.BUSINESS_ARCH,
            version=req_info["version"],
            create_dir=True
        )
        
        # 保存需求分析报告
        analysis_report = await self._save_analysis_report(
            req_info["req_id"],
            parse_result.instruct_content,
            version=req_info["version"]
        )
        
        return {
            "biz_req_id": parse_result.instruct_content["requirement_id"],
            "architecture_file": str(biz_arch_path),  # 使用服务生成的路径
            "user_stories": update_result.instruct_content["user_stories"],
            "version": req_info["version"],
            "analysis_report": str(analysis_report)
        } 

    async def _save_analysis_report(self, req_id: str, data: dict, version: str) -> Path:
        """保存需求分析报告"""
        content = self.doc_manager.template.requirement_analysis(
            req_id=req_id,
            analysis_result=data
        )
        return self.doc_manager.save_document(
            doc_type=DocType.REQUIREMENT_ANALYZED,
            content=content,
            version=version,
            req_id=req_id
        )