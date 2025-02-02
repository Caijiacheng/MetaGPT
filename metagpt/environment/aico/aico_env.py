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
from metagpt.ext.aico.services.spec_service import SpecService


class AICOEnvironment(Environment):
    """AICO项目环境"""
    
    # 消息类型定义（按照新版文档规范）
    MSG_PROJECT_INFO         = "project_info"         # 项目基本信息
    MSG_RAW_REQUIREMENTS     = "raw_requirements"     # 用户输入的原始需求文本
    MSG_USER_STORIES         = "user_stories"         # 经转换后的用户故事列表
    MSG_PARSED_REQUIREMENTS  = "parsed_requirements"  # 解析后的需求（JSON格式，包含：req_id, req_name, req_description, source, priority, status, submitter, submission_time, target_completion_time, acceptance_criteria, remarks）
    MSG_TASKS                = "tasks"                # 任务列表（JSON格式，包含：task_id, related_req_id, related_story_id, task_name, description, type, assignee, status, planned_start, planned_end, actual_start, actual_end, remarks）
    MSG_CODE                 = "code"                 # 代码产出（JSON格式，包含：code_content, unit_tests, deployment_instructions）
    MSG_CODE_REVIEW          = "code_review"          # 代码评审结果（JSON格式，包含：issues, suggestions）
    MSG_UNIT_TEST_RESULT     = "unit_test_result"     # 单元测试结果（JSON格式描述）
    MSG_TECH_DESIGN          = "tech_design"          # 技术方案设计文档（JSON格式）
    MSG_4A_ASSESSMENT        = "4a_assessment"        # 4A评估结果（JSON格式，包含：introduction, business_architecture, application_architecture, data_architecture, technical_architecture）
    MSG_ARCH_DESIGN          = "arch_design"          # 架构设计文档（JSON格式，包含详细设计方案、图表使用mermaid语法）
    MSG_PRODUCT_DOCS         = "product_docs"         # 产品文档（JSON格式）
    MSG_REQUIREMENT_ANALYSIS = "requirement_analysis" # 需求分析报告（JSON格式）
    MSG_PRD                  = "prd"                  # PRD文档（JSON格式，包含：product_overview, functional_requirements, non_functional_requirements, acceptance_criteria）
    MSG_PRD_REVISED          = "prd_revised"          # 修订后的PRD
    MSG_PRODUCT_DESIGN       = "product_design"       # 产品设计方案中间产物（JSON格式）
    MSG_PRODUCT_DESIGNED     = "product_designed"     # 产品设计的最终产出（JSON格式）
    MSG_DEV_ENV              = "dev_env"              # 开发环境配置（JSON格式描述）
    MSG_BUG_REPORT           = "bug_report"           # 缺陷报告（JSON格式，包含：bug_id, description, reproduction_steps, analysis, fix_suggestions）
    MSG_TEST_CASES           = "test_cases"           # 测试用例（JSON格式，包含：test_case_id, description, steps, expected_results, test_data）
    MSG_TEST_RESULTS         = "test_results"         # 测试结果（JSON格式描述详细执行记录）
    MSG_DEBUG_RESULT         = "debug_result"         # 代码调试结果（JSON格式）

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
        
        # 从环境变量获取全局规范路径
        global_spec_path = os.getenv("AICO_GLOBAL_SPEC_PATH", "docs/aico/specs")
        global_spec_root = Path(global_spec_path)
        
        # 初始化规范服务（完全解耦路径管理）
        self.spec_service = SpecService(
            global_spec_root=global_spec_root,
            project_root=self.project_root
        )
        
        # 仅初始化项目规范模板（不执行同步）
        for spec_type in ["ea_design", "project_tracking"]:
            self.spec_service.init_project_spec(spec_type)
        
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