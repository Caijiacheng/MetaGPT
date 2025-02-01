#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : aico_env.py
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from metagpt.environment.base_env import Environment


class AICOEnvironment(Environment):
    """AICO项目环境"""
    
    # 消息类型定义
    MSG_PROJECT_INFO = "project_info"  # 项目基本信息
    MSG_RAW_REQUIREMENTS = "raw_requirements"  # 原始需求
    MSG_USER_STORIES = "user_stories"  # 用户故事
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.project_root: Path = None
        self.docs_root: Path = None
        self.tracking_root: Path = None
        
    def init_project(self, project_name: str, root_dir: Path):
        """初始化项目目录"""
        self.project_root = root_dir / project_name
        self.docs_root = self.project_root / "docs"
        self.tracking_root = self.docs_root / "tracking"
        
        # 创建必要的目录
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.docs_root.mkdir(parents=True, exist_ok=True)
        self.tracking_root.mkdir(parents=True, exist_ok=True)
        
    def get_doc_path(self, doc_type: str) -> Path:
        """获取文档路径"""
        doc_paths = {
            "requirements": self.docs_root / "requirements.md",
            "user_stories": self.docs_root / "user_stories.md",
        }
        return doc_paths.get(doc_type)

    def get_tracking_file(self, file_type: str) -> Path:
        """获取跟踪文件路径"""
        tracking_files = {
            "requirements": self.tracking_root / "需求跟踪.xlsx",
            "tasks": self.tracking_root / "任务跟踪.xlsx"
        }
        return tracking_files.get(file_type)