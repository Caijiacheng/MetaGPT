# 测试 @metagpt/ext/aico/services/version_manager.py
## 测试的目录和数据放在 @tests/data/aico/services/version_manager
## 测试要求：
### 模拟外部调用的场景，测试完整的版本管理流程workflow，可以调用到所有的函数 
### 针对每个函数，提供单元测试，确保函数功能正确，并且有异常测试的场景，覆盖到80%以上的代码

# 运行测试
# pytest tests/metagpt/ext/aico/services/test_version_manager.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/version_manager.py"

import pytest
from pathlib import Path
from unittest import mock
from metagpt.ext.aico.services.version_manager import (
    AICOVersionManager,
    get_current_version,
    update_version_file
)
import logging

@pytest.fixture
def tmp_project(tmp_path):
    # 准备测试项目目录
    project = tmp_path / "test_project"
    project.mkdir()
    return project

def test_load_existing_version(tmp_project):
    # 测试已有VERSION文件的加载
    version_file = tmp_project / "VERSION"
    version_file.write_text("1.2.3\n")
    
    manager = AICOVersionManager(tmp_project)
    assert manager.current_version == "1.2.3"

def test_init_new_project(tmp_project):
    # 测试新项目初始化
    manager = AICOVersionManager(tmp_project)
    assert (tmp_project / "VERSION").exists()
    assert manager.current_version == "0.1.0"

def test_validate_version_failure(tmp_project):
    # 测试版本格式校验失败场景
    manager = AICOVersionManager(tmp_project)
    
    # 测试无效版本格式
    invalid_versions = [
        "1.0",          # 缺少patch版本
        "a.1.0",        # 非数字major版本
        "1.b.0",        # 非数字minor版本
        "1.1.c",        # 非数字patch版本
        "1.0.0.1",      # 版本段过多
        "version1.0.0"  # 包含非数字字符
    ]
    
    for version in invalid_versions:
        with pytest.raises(ValueError) as e:
            manager.validate_version(version)
        assert f"无效版本格式: {version}" in str(e.value)

def test_generate_first_release_success(tmp_project):
    # 测试生成首个正式版本
    manager = AICOVersionManager(tmp_project)
    new_version = manager.generate_first_release()
    assert new_version == "1.0.0"
    assert (tmp_project / "VERSION").read_text().strip() == "1.0.0"

def test_generate_first_release_failure(tmp_project):
    # 测试非法生成首个版本
    manager = AICOVersionManager(tmp_project)
    manager.current_version = "0.2.0"
    with pytest.raises(ValueError) as e:
        manager.generate_first_release()
    assert "只能在初始化版本生成首个正式版本" in str(e.value)

@pytest.mark.parametrize("change_type, expected", [
    ("major", "2.0.0"),
    ("minor", "1.1.0"),
    ("patch", "1.0.1")
])
def test_bump_versions(tmp_project, change_type, expected):
    # 参数化测试版本升级
    (tmp_project / "VERSION").write_text("1.0.0\n")
    manager = AICOVersionManager(tmp_project)
    new_version = manager.bump(change_type)
    assert new_version == expected
    assert get_current_version(tmp_project) == expected

def test_invalid_bump_type(tmp_project):
    # 测试无效升级类型
    manager = AICOVersionManager(tmp_project)
    with pytest.raises(ValueError) as e:
        manager.bump("invalid")
    assert "无效变更类型: invalid" in str(e.value)

def test_get_current_version_fallback(tmp_project):
    # 测试版本文件缺失时的默认值
    version = get_current_version(tmp_project)
    assert version == "1.0.0"

def test_corrupted_version_file(tmp_project, caplog):
    # 测试损坏的版本文件处理
    version_file = tmp_project / "VERSION"
    version_file.write_text("invalid-version")
    
    version = get_current_version(tmp_project)
    assert version == "1.0.0"
    assert "VERSION文件格式错误" in caplog.text

def test_full_workflow(tmp_project):
    # 测试完整工作流程
    # 1. 初始化新项目
    manager = AICOVersionManager(tmp_project)
    assert manager.current_version == "0.1.0"
    
    # 2. 生成首个正式版本
    manager.generate_first_release()
    assert manager.current_version == "1.0.0"
    
    # 3. 进行多次版本升级
    assert manager.bump("minor") == "1.1.0"
    assert manager.bump("patch") == "1.1.1"
    assert manager.bump("major") == "2.0.0"
    
    # 4. 验证文件持久化
    new_manager = AICOVersionManager(tmp_project)
    assert new_manager.current_version == "2.0.0"

def test_update_version_file_logging(tmp_project, caplog):
    # 设置日志级别
    with caplog.at_level(logging.INFO):
        update_version_file(tmp_project, "2.3.4")
    assert "版本文件已更新: 2.3.4" in caplog.text
    assert (tmp_project / "VERSION").read_text().strip() == "2.3.4"

def test_validate_version_success(tmp_project):
    manager = AICOVersionManager(tmp_project)
    
    valid_versions = [
        "0.1.0",
        "1.0.0",
        "2.3.4",
        "10.20.30",
        "999.999.999"
    ]
    
    for version in valid_versions:
        # 应该不抛出异常
        manager.validate_version(version)

