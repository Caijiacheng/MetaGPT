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
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AICOBusinessAnalyst(AICOBaseRole):
    """遵循AICO规范的业务分析师角色"""
    
    name: str = "AICO_BA"
    profile: str = "Business Analyst"
    goal: str = "解析业务需求并维护业务架构"
    constraints: str = "严格遵循AICO业务需求规范"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ParseBizRequirement, Update4ABusiness])
        
    async def _act(self) -> None:
        """纯消息驱动模式（文档5.2节）"""
        async for msg in self.observe(AICOEnvironment.MSG_REQ_BIZ_ANALYSIS):
            try:
                # 通知PM分析开始
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_STARTED, {
                    "req_id": msg.content["req_id"]
                })
                
                result = await self._process_requirement(msg.content)
                
                # 生成用户故事文档
                stories_file = self._save_user_stories(result["biz_req_id"], result["version"])
                
                # 返回处理结果给PM
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_DONE, {
                    "req_id": msg.content["req_id"],
                    "biz_req_id": result["biz_req_id"],
                    "architecture_file": result["architecture_file"],
                    "user_stories_file": str(stories_file)
                })
                
            except Exception as e:
                logger.error(f"需求分析失败: {msg.content['req_id']}")
                await self.publish(AICOEnvironment.MSG_BA_ANALYSIS_FAILED, {
                    "req_id": msg.content["req_id"],
                    "error": str(e)
                })

    def _save_user_stories(self, project_id: str, version: str) -> Path:
        """生成独立版本的用户故事文档"""
        stories_dir = self.project_root / "docs/requirements/user_stories"
        stories_dir.mkdir(parents=True, exist_ok=True)
        
        # 版本文件路径
        filename = f"{project_id}_user_stories_v{version}.md"
        file_path = stories_dir / filename
        
        # 仅当文件不存在时创建新版本
        if not file_path.exists():
            content = self._generate_story_content(version)
            file_path.write_text(content, encoding="utf-8")
        else:
            logger.warning(f"用户故事版本已存在: {filename}")
        
        return file_path

    def _generate_story_content(self, version: str) -> str:
        """生成当前版本内容"""
        content = f"# 项目用户故事（版本: {version}）\n\n"
        content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for std_req_id, story_list in self.user_stories.items():
            content += f"## 标准需求 {std_req_id}\n"
            for story in story_list:
                content += f"### 用户故事 {story['story_id']}\n"
                content += f"**标题**: {story['title']}\n"
                content += f"**状态**: {story['status']}\n"
                content += f"**验收标准**:\n{story['acceptance_criteria']}\n\n"
        return content

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
        
        return {
            "biz_req_id": parse_result.instruct_content["requirement_id"],
            "architecture_file": str(self.project_root / "docs/ea/biz_architecture.md"),
            "user_stories": update_result.instruct_content["user_stories"],
            "version": req_info["version"]
        } 