# 测试 @metagpt/ext/aico/services/version_manager.py
## version_manager代码目标覆盖率：80%以上
## 测试的目录和数据放在 @tests/data/aico/services/version_manager


# 运行测试
# pytest tests/metagpt/ext/aico/services/test_version_manager.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/*.py"

import pytest
from pathlib import Path
from datetime import datetime
from metagpt.ext.aico.services.version_manager import (
    AICOVersionManager,
    get_current_version,
    update_version
)
from metagpt.utils.git_repository import GitRepository

TEST_DATA_DIR = Path(__file__).parent.parent / "data/aico/services/version_manager"

@pytest.fixture
def version_file(tmp_path):
    return tmp_path / "VERSION"

@pytest.fixture
def repo_with_versions(tmp_path):
    # 初始化Git仓库并创建测试版本文件
    repo = GitRepository(local_path=tmp_path, auto_init=True)
    (tmp_path / "VERSION").write_text("1.0.0")
    repo.add_change(tmp_path / "VERSION")
    repo.commit("init version")
    return tmp_path

class TestVersionManagerBasics:
    def test_file_creation(self, version_file):
        """测试版本文件初始化"""
        manager = AICOVersionManager(version_file)
        assert version_file.exists()
        assert version_file.read_text().strip() == "0.1.0"

    def test_get_current_version(self, repo_with_versions):
        """测试获取当前版本"""
        version = get_current_version(repo_with_versions)
        assert version == "1.0.0"

class TestVersionOperations:
    @pytest.mark.parametrize("bump_type, expected", [
        ("major", "2.0.0"),
        ("minor", "1.1.0"),
        ("patch", "1.0.1"),
    ])
    def test_bump_version(self, repo_with_versions, bump_type, expected):
        """测试版本号递增"""
        manager = AICOVersionManager(repo_with_versions / "VERSION")
        new_version = manager.bump_version(bump_type)
        assert new_version == expected
        assert get_current_version(repo_with_versions) == expected

    def test_add_version_record(self, repo_with_versions):
        """测试添加版本记录"""
        manager = AICOVersionManager(repo_with_versions / "VERSION")
        test_data = {
            "doc_path": "docs/v1.0.0",
            "doc_type": "PRD",
            "change_type": "新增",
            "changes": ["需求管理功能"],
            "related_reqs": ["REQ-001"]
        }
        
        manager.add_version_record(**test_data)
        history = manager.get_version_history()
        
        assert len(history) == 1
        assert history[0]["version"] == "1.0.0"
        assert "需求管理功能" in history[0]["changes"]

class TestVersionHistory:
    def test_history_ordering(self, repo_with_versions):
        """测试版本历史排序"""
        manager = AICOVersionManager(repo_with_versions / "VERSION")
        
        # 添加多个版本记录
        for i in range(3):
            manager.bump_version("patch")
            manager.add_version_record(
                doc_path=f"docs/v1.0.{i+1}",
                doc_type="设计文档",
                change_type="更新",
                changes=[f"补丁更新{i+1}"],
                related_reqs=[]
            )
        
        history = manager.get_version_history()
        versions = [h["version"] for h in history]
        assert versions == ["1.0.3", "1.0.2", "1.0.1", "1.0.0"]

class TestVersionCleanup:
    @pytest.fixture
    def multi_versions(self, repo_with_versions):
        """创建多版本测试数据"""
        manager = AICOVersionManager(repo_with_versions / "VERSION")
        
        # 生成测试版本序列
        versions = []
        for _ in range(2):  # 主版本
            manager.bump_version("major")
            versions.append(manager.current_version)
            for _ in range(3):  # 次版本
                manager.bump_version("minor")
                versions.append(manager.current_version)
                for _ in range(2):  # 修订版
                    manager.bump_version("patch")
                    versions.append(manager.current_version)
        return versions

    def test_cleanup_policy(self, repo_with_versions, multi_versions):
        """测试版本清理策略"""
        manager = AICOVersionManager(repo_with_versions / "VERSION")
        
        # 应用保留策略
        retention = {"major": 2, "minor": 2, "patch": 1}
        manager.clean_old_versions(retention)
        
        # 验证保留结果
        remaining = manager.get_version_history()
        versions = [h["version"] for h in remaining]
        
        # 预期保留版本模式
        expected_patterns = [
            "3.2.1", "3.2.0",
            "3.1.1", 
            "2.2.1", "2.2.0",
            "2.1.1"
        ]
        assert all(v in versions for v in expected_patterns)

class TestEdgeCases:
    def test_invalid_version_format(self, tmp_path):
        """测试无效版本格式处理"""
        version_file = tmp_path / "VERSION"
        version_file.write_text("invalid")
        
        with pytest.raises(ValueError):
            AICOVersionManager(version_file)

    def test_empty_version_file(self, tmp_path):
        """测试空版本文件初始化"""
        version_file = tmp_path / "VERSION"
        manager = AICOVersionManager(version_file)
        assert manager.current_version == "0.1.0"