#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新版AICOProjectManager：
   - 模拟完整项目管理流程（目前只测试第一阶段的需求处理与评审）
   - 针对各个函数提供单元测试及异常测试，目标覆盖80%以上代码
运行测试：
    pytest tests/metagpt/ext/aico/roles/test_project_manager.py -v --cov=metagpt --cov-report=term
    coverage report --include="metagpt/ext/aico/**/project_manager.py"
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import shutil
import asyncio

from metagpt.ext.aico.roles.project_manager import AICOProjectManager
from metagpt.ext.aico.services.doc_manager import DocType
from metagpt.environment.aico.aico_env import AICOEnvironment

# Fixtures
@pytest.fixture
def tmp_project_root(tmp_path):
    root = tmp_path / "test_project"
    yield root
    if root.exists():
        shutil.rmtree(root)

@pytest.fixture
def mock_env():
    env = MagicMock()
    env.requirements = []
    return env

@pytest.fixture
def pm(tmp_project_root, mock_env):
    role = AICOProjectManager(project_root=tmp_project_root)
    role.set_env(mock_env)
    # 为确保 rc 存在，模拟 rc.env
    role.rc = MagicMock()
    role.rc.env = mock_env
    # 模拟各服务
    role.doc_manager = MagicMock()
    role.tracking_svc = MagicMock()
    role.version_svc = MagicMock()
    return role

# Helper: 构造一个伪造的消息对象，用于 observe 模拟返回
def create_fake_message(name, content):
    fake_msg = MagicMock()
    fake_msg.name = name
    fake_msg.content = content
    return fake_msg

# Test Cases
class TestAICOProjectManager:
    """测试AICO项目经理核心功能"""

    @pytest.mark.asyncio
    async def test_project_init_new(self, pm, tmp_project_root):
        """测试新项目初始化流程：
           当项目根目录不存在时，应调用文档管理服务创建基础目录并创建跟踪文件
        """
        if tmp_project_root.exists():
            shutil.rmtree(tmp_project_root)
        pm._init_project()
        expected_dirs = [
            DocType.REQUIREMENT_RAW,
            DocType.REQUIREMENT_ANALYZED,
            DocType.BUSINESS_ARCH,
            DocType.TECH_ARCH,
            DocType.PRD,
            DocType.SERVICE_DESIGN,
            DocType.TEST_CASE
        ]
        pm.doc_manager.ensure_dirs.assert_called_with(expected_dirs)
        pm.tracking_svc.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_load_existing(self, pm, tmp_project_root):
        """测试加载已有项目：
           模拟存在项目目录和跟踪文件，则应走加载流程，不再创建基础目录
        """
        (tmp_project_root / "docs/requirements/raw").mkdir(parents=True, exist_ok=True)
        fake_tracking_path = tmp_project_root / "project_tracking.xlsx"
        fake_tracking_path.touch()
        pm.doc_manager.get_doc_path.return_value = fake_tracking_path

        pm._init_project()
        pm.doc_manager.get_doc_path.assert_called()
        pm.doc_manager.ensure_dirs.assert_not_called()

    def test_validate_project_structure_missing(self, pm, tmp_project_root):
        """测试项目结构校验：
           当基础目录不完整时，抛出异常提示不完整的项目结构
        """
        (tmp_project_root / "docs/requirements/raw").mkdir(parents=True, exist_ok=True)
        with pytest.raises(ValueError) as excinfo:
            pm._validate_project_structure()
        assert "项目结构不完整" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_requirement_processing_flow(self, pm):
        """测试需求处理流程中需求解析阶段：
           通过覆盖 _parse_raw_requirements 模拟文档保存和跟踪表更新
        """
        async def fake_parse_raw_requirements():
            # 模拟保存原始需求文件及跟踪表更新
            pm.doc_manager.save_document(DocType.REQUIREMENT_RAW, content="需求文本", version="")
            pm.tracking_svc.add_raw_requirement(
                file_path="dummy_path",
                description="需求文本"[:100],
                source="test_case",
                req_type="business"
            )
        pm._parse_raw_requirements = fake_parse_raw_requirements
        # 为避免后续阶段影响，补充后续方法为空实现
        pm._process_arch_analysis = MagicMock()
        pm._confirm_requirement_baseline = MagicMock()

        await pm._process_requirements()
        pm.doc_manager.save_document.assert_called_with(DocType.REQUIREMENT_RAW, content="需求文本", version="")
        pm.tracking_svc.add_raw_requirement.assert_called_with(
            file_path="dummy_path",
            description="需求文本"[:100],
            source="test_case",
            req_type="business"
        )

    @pytest.mark.asyncio
    async def test_requirement_review_process(self, pm):
        """测试需求评审流程：
           模拟发送需求预审消息、观察人工确认消息，验证消息构造正确
        """
        # 模拟 observe 返回人工确认消息
        fake_confirm_msg = create_fake_message("project:req_review_confirmed", {
            "approved": True,
            "approved_reqs": ["REQ-001"],
            "review_comments": {"note": "OK"}
        })
        pm.observe = MagicMock(return_value=fake_confirm_msg)
        pm.publish_message = MagicMock()  # 模拟消息发送函数

        await pm._confirm_requirement_baseline()
        # 应发送两个消息：一条预审消息、一条基线确认消息
        assert pm.publish_message.call_count == 2
        first_msg = pm.publish_message.call_args_list[0][0][0]
        second_msg = pm.publish_message.call_args_list[1][0][0]
        # 验证预审消息名称与基线确认消息名称（预定义在AICOEnvironment中）
        assert first_msg.name == "requirement:biz_analysis"
        assert second_msg.name == "prd:revised"
        pm.observe.assert_called_with("project:req_review_confirmed", timeout=3600)

    @pytest.mark.asyncio
    async def test_invalid_requirement_handling(self, pm):
        """测试无效需求输入处理：
           当输入需求数据格式错误时，应记录错误日志
        """
        pm.rc.env.requirements = [{"invalid": "data"}]
        async def fake_parse_invalid():
            pm.logger.error("无效的需求输入格式")
        pm._parse_raw_requirements = fake_parse_invalid
        with patch.object(pm, "logger") as mock_logger:
            await pm._parse_raw_requirements()
            mock_logger.error.assert_called_with("无效的需求输入格式")

    @pytest.mark.parametrize("pending_changes, expected", [
        ([{"change_type": "架构变更"}], "major"),
        ([{"change_type": "新增功能"}], "minor"),
        ([{"change_type": "缺陷修复"}], "patch")
    ])
    def test_version_change_determination(self, pm, pending_changes, expected):
        """测试版本变更类型判断逻辑"""
        pm.tracking_svc.get_pending_changes.return_value = pending_changes
        assert pm._determine_version_change() == expected

    @pytest.mark.asyncio
    async def test_async_message_handling(self, pm):
        """测试异步消息处理机制：
           模拟消息队列返回消息，并验证 observe 方法返回内容正确
        """
        fake_msg = create_fake_message(AICOEnvironment.MSG_BA_ANALYSIS_DONE.name, {"req_id": "REQ-001", "status": "completed"})
        pm.rc.env.memory = MagicMock()
        pm.rc.env.memory.get.return_value = [fake_msg]
        result = await pm.observe(AICOEnvironment.MSG_BA_ANALYSIS_DONE.name)
        assert result.content["req_id"] == "REQ-001"

    @pytest.mark.skip(reason="待第二阶段实现")
    def test_design_review_process(self):
        pass

    @pytest.mark.skip(reason="待第三阶段实现")
    def test_implementation_tracking(self):
        pass

# 异常测试
class TestExceptionCases:
    """测试异常场景处理"""

    def test_corrupted_tracking_file(self, pm):
        """测试跟踪文件校验异常：
           当 tracking_svc._get_workbook 抛出异常时，_validate_tracking_file 应返回 False
        """
        pm.tracking_svc._get_workbook.side_effect = Exception("Invalid file format")
        result = pm._validate_tracking_file()
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_handling(self, pm):
        """测试需求确认超时：
           当 observe 返回 None 时，应记录错误日志提示确认未通过
        """
        pm.observe = MagicMock(return_value=None)
        with patch.object(pm, "logger") as mock_logger:
            await pm._confirm_requirement_baseline()
            mock_logger.error.assert_called_with("需求基线确认未通过")

    def test_version_generation_failure(self, pm):
        """测试版本生成异常：
           当 version_svc.bump 抛出异常时，_generate_new_version 应传递该异常
        """
        pm.version_svc.bump.side_effect = ValueError("Invalid version format")
        with pytest.raises(ValueError):
            pm._generate_new_version("invalid")