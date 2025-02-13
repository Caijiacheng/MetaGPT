#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : aico_env.py

说明：
  重构后的AICO项目环境，将消息协议部分从原来的 Message 实例剥离，
  改用独立的 MessageSchema 描述消息格式，避免因 Message.content 必须为字符串而导致校验错误。
"""

import os
import logging
from pathlib import Path
from typing import Any, ClassVar
import json

from pydantic import BaseModel, model_validator, create_model
from metagpt.environment.base_env import Environment
from metagpt.schema import Message


class MessageSchema(Message):
    """
    统一的消息协议模型，继承自 Message。
    增加 content_schema 描述消息内容的预期结构，
    并在初始化时自动将 dict 类型的数据转换为 JSON 字符串，
    同时保存原始结构化数据到 instruct_content 字段.

    content_schema 定义了消息内容的字段要求，格式为：
      {
         "字段名": (类型, 默认值或 Ellipsis)
      }
    默认值为 Ellipsis 表示必填字段，不指定默认值则为可选字段。
    """
    content_schema: dict = {}
    desc: str = ""
    instruct_content: Any = None  # 保存原始字典格式的消息内容，用于解码时优先返回

    @model_validator(mode="before")
    def auto_convert(cls, values: dict) -> dict:
        content = values.get("content")
        if isinstance(content, dict):
            # 如果 content 是 dict，则自动转换为 JSON 字符串并保存原始数据
            values["instruct_content"] = content
            values["content"] = json.dumps(content)
        return values

    def with_content(self, **fields) -> "MessageSchema":
        """
        根据 content_schema 动态构造消息内容。

        利用 pydantic 动态创建消息内部的数据模型对传入字段进行验证，
        如果存在拼写错误或遗漏必填项，将直接抛出 ValidationError。
        """
        if self.content_schema:
            DynamicContentModel = create_model(
                self.name + "Content",
                **self.content_schema
            )
            validated = DynamicContentModel(**fields)
            return self.copy(update={"content": validated.dict()})
        else:
            return self.copy(update={"content": fields})

    def decode_content(self):
        """
        解码消息内容，优先返回存储在 instruct_content 中的原始数据，
        否则尝试从 content（JSON字符串）中解析，并利用 content_schema 定义的字段规则生成动态模型返回。
        """
        if self.instruct_content:
            return self.instruct_content

        try:
            raw = json.loads(self.content)
            if self.content_schema:
                DynamicContentModel = create_model(
                    self.name + "Content",
                    **self.content_schema
                )
                return DynamicContentModel(**raw)
            return raw
        except Exception as e:
            raise ValueError(f"消息内容解析失败: {e}")


class AICOEnvironment(Environment):
    """AICO项目环境"""

    # 常量属性不参与 pydantic 校验，使用 ClassVar 标注
    MSG_PROJECT_INFO: ClassVar[str] = "project_info"
    MSG_RAW_REQUIREMENTS: ClassVar[str] = "raw_requirements"
    MSG_USER_STORIES: ClassVar[str] = "user_stories"

    # 需求分析相关消息协议，添加 ClassVar 类型标注
    MSG_REQUIREMENT_BIZ_ANALYSIS: ClassVar[MessageSchema] = MessageSchema(
        name="requirement:biz_analysis",
        desc="业务需求分析任务",
        content_schema={
            "req_id": (str, ...),          # 必填：需求ID
            "file_path": (str, ...),       # 必填：需求文件路径
            "type": (str, ...),            # 必填：需求类型(business/tech)
            "version": (str, ...)          # 必填：版本号
        },
        content={}
    )
    MSG_REQUIREMENT_TECH_ANALYSIS: ClassVar[MessageSchema] = MessageSchema(
        name="requirement:tech_analysis",
        desc="技术需求分析任务",
        content_schema={
            "req_id": (str, ...),          # 必填：需求ID
            "biz_req_id": (str, ...),      # 必填：关联业务需求ID
            "file_path": (str, ...),       # 必填：需求文件路径
            "version": (str, ...)          # 必填：版本号
        },
        content={}
    )

    # BA 分析流程的消息协议
    MSG_BA_ANALYSIS_STARTED: ClassVar[MessageSchema] = MessageSchema(
        name="ba_analysis:started",
        desc="BA开始分析通知",
        content_schema={
            "req_id": (str, ...),          # 必填：需求ID
            "start_time": (str, ...)       # 必填：开始时间
        },
        content={}
    )

    MSG_BA_ANALYSIS_DONE: ClassVar[MessageSchema] = MessageSchema(
        name="ba_analysis:done",
        desc="BA分析完成通知",
        content_schema={
            "req_id": (str, ...),          # 必填：需求ID
            "standard_req": (dict, ...),   # 必填：标准化需求
            "user_stories": (list, ...),   # 必填：用户故事列表
            "output_files": (list, ...)    # 必填：输出文件列表
        },
        content={}
    )

    MSG_BA_ANALYSIS_FAILED: ClassVar[MessageSchema] = MessageSchema(
        name="ba_analysis:failed",
        desc="BA分析失败通知",
        content_schema={
            "req_id": (str, ...),          # 必填：需求ID
            "error": (str, ...),           # 必填：错误信息
            "fail_time": (str, ...)        # 必填：失败时间
        },
        content={}
    )

    # 架构分析消息协议
    MSG_BUSINESS_ARCH: ClassVar[MessageSchema] = MessageSchema(
        name="architecture:business",
        desc="业务架构分析",
        content_schema={
            "version": (str, ...),         # 必填：版本号
            "biz_requirements": (list, ...)  # 必填：业务需求列表
        },
        content={}
    )

    MSG_TECH_ARCH: ClassVar[MessageSchema] = MessageSchema(
        name="architecture:technical",
        desc="技术架构分析",
        content_schema={
            "version": (str, ...),          # 必填：版本号
            "tech_requirements": (list, ...)  # 必填：技术需求列表
        },
        content={}
    )

    # 评审相关消息协议
    MSG_PRD: ClassVar[MessageSchema] = MessageSchema(
        name="prd:review",
        desc="PRD评审",
        content_schema={
            "version": (str, ...),         # 必填：版本号
            "ai_review": (dict, ...),      # 必填：AI评审结果
            "requirements": (list, ...)    # 必填：需求列表
        },
        content={}
    )

    MSG_PRD_REVISED: ClassVar[MessageSchema] = MessageSchema(
        name="prd:revised",
        desc="PRD修订确认",
        content_schema={
            "version": (str, ...),           # 必填：版本号
            "approved_reqs": (list, ...),      # 必填：通过的需求列表
            "review_comments": (dict, None)    # 可选：评审意见，默认 None
        },
        content={}
    )

    # 任务跟踪消息协议
    MSG_TASK_UPDATE: ClassVar[MessageSchema] = MessageSchema(
        name="task:update",
        desc="任务状态更新",
        content_schema={
            "task_id": (str, ...),         # 必填：任务ID
            "status": (str, ...),          # 必填：任务状态
            "progress": (float, ...),      # 必填：进度百分比
            "update_time": (str, ...)       # 必填：更新时间
        },
        content={}
    )

    # 设计文档相关消息协议
    MSG_DESIGN_DOC_DONE: ClassVar[MessageSchema] = MessageSchema(
        name="design:doc_done",
        desc="设计文档完成通知",
        content_schema={
            "doc_type": (str, ...),          # 必填：文档类型(PRD/TECH_DESIGN)
            "version": (str, ...),           # 必填：版本号
            "file_path": (str, ...),         # 必填：文档路径
            "review_status": (str, ...)       # 必填：评审状态
        },
        content={}
    )

    MSG_DESIGN_BASELINE: ClassVar[MessageSchema] = MessageSchema(
        name="design:baseline",
        desc="设计基线确认",
        content_schema={
            "version": (str, ...),           # 必填：版本号
            "design_type": (str, ...),        # 必填：设计类型(PRD/TECH_DESIGN)
            "review_summary": (dict, ...)     # 必填：评审摘要
        },
        content={}
    )

    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root

        