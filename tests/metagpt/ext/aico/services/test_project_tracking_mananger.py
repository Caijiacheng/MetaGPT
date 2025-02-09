# 测试 @metagpt/ext/aico/services/project_tracking_manager.py
## project_tracking_manager代码目标覆盖率：80%以上
## 测试的目录和数据放在 @tests/data/aico/services/project_tracking_manager


# 运行测试
# pytest tests/metagpt/ext/aico/services/test_project_tracking_mananger.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/*.py"

import pytest
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from metagpt.ext.aico.services.project_tracking_manager import (
    ProjectTrackingManager,
    TrackingSheet
)
from metagpt.ext.aico.config.tracking_config import SheetType

TEST_DATA_DIR = Path(__file__).parent.parent / "data/aico/services/project_tracking_manager"

@pytest.fixture
def test_excel_path(tmp_path):
    return tmp_path / "test_project_tracking.xlsx"

@pytest.fixture
def tracking_manager(test_excel_path):
    # 确保每次测试使用新文件
    if test_excel_path.exists():
        test_excel_path.unlink()
    return ProjectTrackingManager(test_excel_path)

class TestProjectTrackingManagerInit:
    def test_file_creation(self, test_excel_path, tracking_manager):
        """测试文件初始化"""
        assert test_excel_path.exists()
        assert tracking_manager.wb.sheetnames == [
            st.value.name for st in SheetType
        ]

    def test_sheet_headers(self, tracking_manager):
        """测试各工作表表头正确性"""
        for sheet_type in SheetType:
            ws = tracking_manager.wb[sheet_type.value.name]
            assert [cell.value for cell in ws[1]] == sheet_type.value.headers

class TestRawRequirementOperations:
    def test_add_raw_requirement(self, tracking_manager):
        """测试添加原始需求记录"""
        test_data = {
            "file_path": "raw/iter1/test_req.md",
            "req_type": "文档",
            "comment": "测试需求"
        }
        
        tracking_manager.add_raw_requirement(**test_data)
        
        ws = tracking_manager.wb[TrackingSheet.RAW_REQUIREMENTS.value]
        last_row = ws.iter_rows(min_row=2).__next__()
        
        assert last_row[0].value == test_data["file_path"]
        assert last_row[1].value == test_data["req_type"]
        assert last_row[8].value == test_data["comment"]
        assert last_row[3].value == "待分析"

    def test_update_raw_requirement_status(self, tracking_manager):
        """测试更新原始需求状态"""
        # 准备测试数据
        file_path = "raw/iter1/status_test.md"
        tracking_manager.add_raw_requirement(file_path, "文档")
        
        # 执行状态更新
        update_time = datetime(2024, 6, 1, 10, 0)
        result = tracking_manager.update_raw_requirement_status(
            file_path, "已分析", update_time
        )
        
        assert result is True
        status = tracking_manager.get_raw_requirement_status(file_path)
        assert status["status"] == "已分析"
        assert status["ba_time"] == update_time

class TestRequirementManagement:
    def test_add_standard_requirement(self, tracking_manager):
        """测试添加标准需求"""
        req_data = {
            "id": "REQ-001",
            "raw_file": "raw/iter1/test_req.md",
            "name": "测试需求",
            "description": "需求描述",
            "source": "内部优化",
            "priority": "高",
            "status": "已提出",
            "owner": "张经理",
            "submit_time": "2024-06-01",
            "due_date": "2024-06-30",
            "acceptance": "验收标准",
            "notes": "测试备注"
        }
        
        tracking_manager.add_standard_requirement(req_data)
        
        ws = tracking_manager.wb[TrackingSheet.REQUIREMENT_MGMT.value]
        last_row = ws.iter_rows(min_row=2).__next__()
        
        assert last_row[0].value == req_data["id"]
        assert last_row[2].value == req_data["name"]
        assert last_row[5].value == req_data["priority"]

class TestUserStoryOperations:
    def test_user_story_lifecycle(self, tracking_manager):
        """测试用户故事全生命周期"""
        # 添加用户故事
        story_data = {
            "story_id": "US-001",
            "related_req_id": "REQ-001",
            "name": "测试用户故事",
            "description": "As a...",
            "priority": "高",
            "status": "待拆分",
            "acceptance": "验收标准",
            "notes": "测试备注"
        }
        tracking_manager.add_user_story(story_data)
        
        # 验证添加
        ws = tracking_manager.wb[TrackingSheet.USER_STORY_MGMT.value]
        last_row = ws.iter_rows(min_row=2).__next__()
        assert last_row[0].value == story_data["story_id"]
        
        # 更新状态
        tracking_manager.update_user_story_status("US-001", "开发中")
        assert last_row[5].value == "开发中"

class TestTaskTracking:
    def test_task_operations(self, tracking_manager):
        """测试任务跟踪全流程"""
        # 添加任务
        task_data = {
            "task_id": "T-001",
            "related_req_id": "REQ-001",
            "related_story_id": "US-001",
            "name": "开发任务",
            "description": "任务描述",
            "type": "开发",
            "owner": "李工",
            "plan_start": "2024-06-01",
            "plan_end": "2024-06-05",
            "notes": "测试任务"
        }
        tracking_manager.add_task(task_data)
        
        # 验证初始状态
        ws = tracking_manager.wb[TrackingSheet.TASK_TRACKING.value]
        last_row = ws.iter_rows(min_row=2).__next__()
        assert last_row[7].value == "待开始"
        
        # 更新状态
        tracking_manager.update_task_status("T-001", "进行中")
        assert last_row[7].value == "进行中"
        assert last_row[9].value is not None  # 实际开始时间

class TestVersionManagement:
    def test_version_records(self, tracking_manager):
        """测试版本记录管理"""
        version = "1.0.0"
        tracking_manager.add_version_record(
            version=version,
            doc_path="docs/v1.0.0",
            doc_type="PRD",
            change_type="新增",
            changes=["新增需求管理功能"],
            related_reqs=["REQ-001"]
        )
        
        history = tracking_manager.get_version_history()
        assert len(history) == 1
        record = history[0]
        assert record["version"] == version
        assert "需求管理功能" in record["changes"][0]

class TestValidation:
    def test_file_structure_validation(self, tracking_manager):
        """测试文件结构校验"""
        assert tracking_manager.validate_file_structure() is True
        
        # 测试异常情况
        del tracking_manager.wb[TrackingSheet.RAW_REQUIREMENTS.value]
        assert tracking_manager.validate_file_structure() is False