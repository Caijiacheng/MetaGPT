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

from metagpt.schemas.message import MessageSchema


class AICOEnvironment(Environment):
    """AICO项目环境"""
    
    # 基础消息类型
    MSG_PROJECT_INFO = "project_info"
    MSG_RAW_REQUIREMENTS = "raw_requirements"
    MSG_USER_STORIES = "user_stories"
    
    # 需求分析相关消息
    MSG_REQUIREMENT_BIZ_ANALYSIS = MessageSchema(
        name="requirement:biz_analysis",
        desc="业务需求分析任务",
        content={
            "req_id": str,          # 需求ID
            "file_path": str,       # 需求文件路径
            "type": str,            # 需求类型(business/tech)
            "version": str          # 版本号
        }
    )
    
    MSG_REQUIREMENT_TECH_ANALYSIS = MessageSchema(
        name="requirement:tech_analysis",
        desc="技术需求分析任务",
        content={
            "req_id": str,          # 需求ID
            "biz_req_id": str,      # 关联业务需求ID
            "file_path": str,       # 需求文件路径
            "version": str          # 版本号
        }
    )
    
    # BA分析流程消息
    MSG_BA_ANALYSIS_STARTED = MessageSchema(
        name="ba_analysis:started",
        desc="BA开始分析通知",
        content={
            "req_id": str,          # 需求ID
            "start_time": str       # 开始时间
        }
    )
    
    MSG_BA_ANALYSIS_DONE = MessageSchema(
        name="ba_analysis:done",
        desc="BA分析完成通知",
        content={
            "req_id": str,          # 需求ID
            "standard_req": dict,    # 标准化需求
            "user_stories": list,    # 用户故事列表
            "output_files": list     # 输出文件列表
        }
    )
    
    MSG_BA_ANALYSIS_FAILED = MessageSchema(
        name="ba_analysis:failed",
        desc="BA分析失败通知",
        content={
            "req_id": str,          # 需求ID
            "error": str,           # 错误信息
            "fail_time": str        # 失败时间
        }
    )
    
    # 架构分析消息
    MSG_BUSINESS_ARCH = MessageSchema(
        name="architecture:business",
        desc="业务架构分析",
        content={
            "version": str,         # 版本号
            "biz_requirements": list # 业务需求列表
        }
    )
    
    MSG_TECH_ARCH = MessageSchema(
        name="architecture:technical",
        desc="技术架构分析",
        content={
            "version": str,         # 版本号
            "tech_requirements": list # 技术需求列表
        }
    )
    
    # 评审相关消息
    MSG_PRD = MessageSchema(
        name="prd:review",
        desc="PRD评审",
        content={
            "version": str,         # 版本号
            "ai_review": dict,      # AI评审结果
            "requirements": list     # 需求列表
        }
    )
    
    MSG_PRD_REVISED = MessageSchema(
        name="prd:revised",
        desc="PRD修订确认",
        content={
            "version": str,         # 版本号
            "approved_reqs": list,  # 通过的需求列表
            "review_comments": dict  # 评审意见
        }
    )
    
    # 任务跟踪消息
    MSG_TASK_UPDATE = MessageSchema(
        name="task:update",
        desc="任务状态更新",
        content={
            "task_id": str,         # 任务ID
            "status": str,          # 任务状态
            "progress": float,      # 进度百分比
            "update_time": str      # 更新时间
        }
    )

    def __init__(
        self,
        project_root: Path,
    ):
        super().__init__()
        self.project_root = project_root

        