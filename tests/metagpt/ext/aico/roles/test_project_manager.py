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
from unittest.mock import MagicMock, patch, call, PropertyMock
from pathlib import Path
import shutil
import asyncio
from unittest.mock import AsyncMock

from metagpt.ext.aico.services.project_tracking_manager import ProjectTrackingManager
from metagpt.ext.aico.roles.project_manager import AICOProjectManager
from metagpt.ext.aico.services.doc_manager import DocType,AICODocManager
from metagpt.environment.aico.aico_env import AICOEnvironment
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM
from metagpt.ext.aico.services.version_manager import AICOVersionManager


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
def mock_llm():
    return MockLLM()

@pytest.fixture
def mock_embedding():
    return MockEmbedding(
        embed_dim=1536,
        model_name="test-embedding",
        callback_manager=MagicMock(),
        embed_batch_size=32
    )



@pytest.fixture
def pm(tmp_project_root, mock_env, mock_embedding, mock_llm):
    """使用真实服务组件初始化项目经理"""
    # 为 ProjectTrackingManager 添加 get_tracked_files 方法，返回空列表
    ProjectTrackingManager.get_tracked_files = lambda self: []
    # 初始化文档服务（需确保AICODocManager.from_repo参数正确）
    doc_manager = AICODocManager.from_repo(
        tmp_project_root,  # 位置参数传递项目根目录
        specs=[],
        embed_model=mock_embedding,  # 注入mock的embedding
        llm=mock_llm  # 注入mock的llm
    )
    
    # 初始化版本服务
    version_svc = AICOVersionManager.from_path(tmp_project_root)
    
    # 初始化跟踪服务
    tracking_path = doc_manager.get_path(DocType.PROJECT_TRACKING)
    tracking_path.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    tracking_svc = ProjectTrackingManager.from_path(
        tracking_path,
    )
    
    # 构造项目经理实例
    role = AICOProjectManager(
        project_root=tmp_project_root,
        doc_manager=doc_manager,
        version_svc=version_svc,
        tracking_svc=tracking_svc
    )
    role.set_env(mock_env)
    return role

@pytest.fixture(autouse=True)
def setup_mocks(mock_llm):
    # 创建模拟的LLM Metadata
    mock_metadata = MagicMock()
    mock_metadata.context_window = 4096  # 典型值
    mock_metadata.num_output = 256
    mock_metadata.model_name = "test-model"
    
    # 使用PropertyMock包装metadata属性
    type(mock_llm).metadata = PropertyMock(return_value=mock_metadata)

# Helper: 构造一个伪造的消息对象，用于 observe 模拟返回
def create_fake_message(name, content):
    fake_msg = MagicMock()
    fake_msg.name = name
    fake_msg.content = content
    return fake_msg

# 测试用例组
class TestAICOProjectManager:
    """测试核心业务逻辑"""
    
    @pytest.fixture(autouse=True)
    def mock_response_synthesizer(self, mocker):
        mocker.patch(
            "metagpt.rag.engines.simple.get_response_synthesizer",
            return_value=MagicMock()
        )
    
    def test_project_init_creates_files(self, pm, tmp_project_root):
        """测试项目初始化创建必要文件"""
        # When
        pm.run(n_round=1)  # 使用实际存在的入口方法
        
        # Then
        assert (tmp_project_root / "VERSION").exists()
        assert (tmp_project_root / "docs/specs").exists()
        assert (tmp_project_root / "project_tracking.xlsx").exists()
    
    @pytest.mark.asyncio
    async def test_requirement_processing_flow(self, pm, tmp_project_root):
        """测试端到端需求处理流程"""
        # Given
        test_req = {
            "file_path": "raw/iter1/req1.md",
            "description": "测试需求",
            "source": "用户提交"
        }
        
        # When
        await pm._process_requirements()
        
        # Then
        tracking_file = tmp_project_root / "project_tracking.xlsx"
        assert tracking_file.exists()
        
        # 验证跟踪文件内容
        tracking_svc = ProjectTrackingManager.from_path(tracking_file)
        assert len(tracking_svc.get_pending_requirements()) == 0  # 需求应被处理
    
    @pytest.mark.asyncio
    async def test_version_bump_on_change(self, pm, tmp_project_root):
        """测试需求变更触发版本更新"""
        # Given
        initial_version = pm.version_svc.current
        pm.tracking_svc.add_raw_requirement("raw/iter1/req2.md", "新增需求")
        
        # When
        await pm._act()  # 执行完整生命周期
        
        # Then
        new_version = pm.version_svc.current
        assert new_version != initial_version
        assert (tmp_project_root / "VERSION").read_text() == new_version

class TestExceptionCases:
    """异常场景测试"""
    
    @pytest.mark.asyncio
    async def test_corrupted_tracking_file(self, pm, tmp_project_root):
        """测试跟踪文件损坏时的异常处理"""
        # Given
        tracking_file = tmp_project_root / "project_tracking.xlsx"
        tracking_file.write_text("invalid content")
        
        # When/Then
        with pytest.raises(Exception) as e:
            await pm._act()
        assert "跟踪文件损坏" in str(e.value)
    
    @pytest.mark.asyncio
    async def test_version_conflict(self, pm, tmp_project_root):
        """测试版本文件冲突处理"""
        # Given
        (tmp_project_root / "VERSION").write_text("invalid-version")
        
        # When/Then
        with pytest.raises(ValueError) as e:
            pm.version_svc.bump("minor")
        assert "无效的版本格式" in str(e.value)

