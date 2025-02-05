from pathlib import Path
from openpyxl import load_workbook, Workbook
from datetime import datetime
from enum import Enum
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

from metagpt.ext.aico.config.tracking_config import SheetType


logger = logging.getLogger(__name__)

class TrackingSheet(Enum):
    """跟踪表工作表定义"""
    RAW_REQUIREMENTS = "原始需求"
    REQUIREMENT_MGMT = "需求管理"
    USER_STORY_MGMT = "用户故事管理"
    TASK_TRACKING = "任务跟踪"

@dataclass
class TrackingServiceConfig:
    file_path: Path
    env: str = "prod"

class ProjectTrackingService:
    """项目跟踪服务（Excel实现）"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.wb = self._init_workbook()
        self._setup_sheets()
        
    def _init_workbook(self) -> Workbook:
        """初始化工作簿"""
        if self.file_path.exists():
            return load_workbook(self.file_path)
        return Workbook()
    
    def _setup_sheets(self):
        """根据配置初始化工作表"""
        required_sheets = {st.value.name: st.value.headers for st in SheetType}
        
        # 创建缺失的工作表
        for sheet_name, headers in required_sheets.items():
            if sheet_name not in self.wb.sheetnames:
                ws = self.wb.create_sheet(sheet_name)
                ws.append(headers)
        
        # 删除默认的空白表
        if "Sheet" in self.wb.sheetnames:
            del self.wb["Sheet"]
            
    def add_version_record(
        self, 
        version: str,
        doc_path: str,
        doc_type: str,
        changes: List[str],
        related_reqs: List[str]
    ):
        """添加版本记录（增强版）"""
        ws = self.wb["版本历史"]
        ws.append([
            version,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            doc_path,
            doc_type,
            "\n".join(changes),  # 变更摘要
            ",".join(related_reqs)  # 关联需求IDs
        ])
        
    def get_latest_version(self, doc_type: str) -> str:
        """获取指定类型的最新版本"""
        ws = self.wb["版本历史"]
        versions = [row[0] for row in ws.iter_rows(min_row=2, values_only=True) if row[3] == doc_type]
        return versions[-1] if versions else "1.0.0"
    
    # 原始需求表操作 --------------------------------------------------
    def get_raw_requirement_status(self, file_path: str) -> Optional[Dict]:
        """获取原始需求状态"""
        ws = self.wb[SheetType.RAW_REQUIREMENT.value.name]
        cols = SheetType.RAW_REQUIREMENT.value.columns
        
        for row in ws.iter_rows(min_row=2):
            if row[cols.RAW_FILE_PATH.value].value == file_path:
                return {
                    "status": row[cols.STATUS.value].value,
                    "ba_time": row[cols.BA_PARSE_TIME.value].value
                }
        return None
        
    def update_raw_requirement_status(
        self, 
        file_path: str, 
        status: str,
        update_time: datetime = datetime.now()
    ):
        """更新原始需求状态"""
        ws = self.wb[SheetType.RAW_REQUIREMENT.value.name]
        cols = SheetType.RAW_REQUIREMENT.value.columns
        
        for row in ws.iter_rows(min_row=2):
            if row[cols.RAW_FILE_PATH.value].value == file_path:
                row[cols.STATUS.value].value = status
                if status == "已分析":
                    row[cols.BA_PARSE_TIME.value].value = update_time
                self.wb.save(self.file_path)
                return True
        return False
    
    # 需求管理表操作 --------------------------------------------------
    def add_standard_requirement(self, req_data: dict):
        """添加标准需求记录"""
        ws = self.wb[SheetType.REQUIREMENT_MGMT.value.name]
        cols = SheetType.REQUIREMENT_MGMT.value.columns
        
        new_row = [
            req_data.get("id"),
            req_data.get("raw_file"),
            req_data.get("name"),
            req_data.get("description"),
            req_data.get("source"),
            req_data.get("priority"),
            req_data.get("status"),
            req_data.get("owner"),
            req_data.get("submit_time"),
            req_data.get("due_date"),
            req_data.get("acceptance"),
            req_data.get("notes")
        ]
        ws.append(new_row)
    
    # 用户故事管理操作 --------------------------------------------------
    def add_user_story(self, story_data: dict):
        """添加用户故事记录"""
        ws = self.wb[SheetType.USER_STORY.value.name]
        cols = SheetType.USER_STORY.value.columns
        
        new_row = [
            story_data.get("story_id"),
            story_data.get("related_req_id"),
            story_data.get("name"),
            story_data.get("description"),
            story_data.get("priority"),
            story_data.get("status"),
            story_data.get("acceptance"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            story_data.get("notes")
        ]
        ws.append(new_row)

    def add_task(self, task_data: dict):
        """添加任务记录"""
        ws = self.wb[SheetType.TASK_TRACKING.value.name]
        cols = SheetType.TASK_TRACKING.value.columns
        
        new_row = [
            task_data.get("task_id"),
            task_data.get("related_req_id"),
            task_data.get("related_story_id"),
            task_data.get("name"),
            task_data.get("description"),
            task_data.get("type"),
            task_data.get("owner"),
            "待开始",  # 默认状态
            task_data.get("plan_start"),
            task_data.get("plan_end"),
            None,  # 实际开始时间
            None,  # 实际结束时间
            task_data.get("notes")
        ]
        ws.append(new_row)
        self.wb.save(self.file_path)

    def update_task_status(self, task_id: str, status: str, update_time: datetime = datetime.now()):
        """更新任务状态"""
        ws = self.wb[SheetType.TASK_TRACKING.value.name]
        cols = SheetType.TASK_TRACKING.value.columns
        
        for row in ws.iter_rows(min_row=2):
            if str(row[cols.TASK_ID.value].value) == task_id:
                row[cols.TASK_STATUS.value].value = status
                if status == "进行中" and not row[cols.ACTUAL_START.value].value:
                    row[cols.ACTUAL_START.value].value = update_time
                elif status == "已完成":
                    row[cols.ACTUAL_END.value].value = update_time
                self.wb.save(self.file_path)
                return True
        return False

    def add_raw_requirement(
        self,
        file_path: str,
        req_type: str,
        status: str = "待分析",
        comment: str = ""
    ):
        """添加原始需求记录"""
        ws = self.wb[SheetType.RAW_REQUIREMENT.value.name]
        cols = SheetType.RAW_REQUIREMENT.value.columns
        
        ws.append([
            file_path,
            req_type,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status,
            "",  # 关联需求ID
            None,  # BA解析时间
            None,  # EA解析时间
            None,  # 完成时间
            comment
        ])
        self.wb.save(self.file_path)
        
    def get_pending_requirements(self) -> List[dict]:
        """获取待分析需求"""
        ws = self.wb[SheetType.RAW_REQUIREMENT.value.name]
        cols = SheetType.RAW_REQUIREMENT.value.columns
        
        pending_reqs = []
        for row in ws.iter_rows(min_row=2):
            if row[cols.STATUS.value].value == "待分析":
                pending_reqs.append({
                    "file_path": row[cols.RAW_FILE_PATH.value].value,
                    "req_type": row[cols.REQ_TYPE.value].value,
                    "add_time": row[cols.ADD_TIME.value].value
                })
        return pending_reqs
    
    def update_requirement_status(self, req_id: str, status: str):
        """更新需求状态"""
        ws = self.wb[SheetType.REQUIREMENT_MGMT.value.name]
        cols = SheetType.REQUIREMENT_MGMT.value.columns
        
        for row in ws.iter_rows(min_row=2):
            if str(row[cols.REQ_ID.value].value) == req_id:
                row[cols.REQ_STATUS.value].value = status
                self.wb.save(self.file_path)
                return True
        return False

    def validate_file_structure(self) -> bool:
        """校验文件结构完整性"""
        required_sheets = {st.value.name for st in SheetType}
        existing_sheets = set(self.wb.sheetnames)
        
        # 检查必需工作表是否存在
        if not required_sheets.issubset(existing_sheets):
            return False
        
        # 检查各表头是否正确
        for sheet_type in SheetType:
            ws = self.wb[sheet_type.value.name]
            expected_headers = sheet_type.value.headers
            actual_headers = [cell.value for cell in ws[1]]  # 第一行为表头
            if actual_headers != expected_headers:
                return False
        
        return True

    def update_requirement(self, req_id: str, **kwargs):
        """更新需求信息"""
        ws = self.wb[SheetType.REQUIREMENT_MGMT.value.name]
        cols = SheetType.REQUIREMENT_MGMT.value.columns
        
        for row in ws.iter_rows(min_row=2):
            if str(row[cols.REQ_ID.value].value) == req_id:
                for field, value in kwargs.items():
                    col = getattr(cols, field.upper(), None)
                    if col and col.name.lower() == field.lower():
                        row[col.value].value = value
                self.wb.save(self.file_path)
                return True
        return False

    def _get_column_index(self, sheet_type: SheetType, header: str) -> int:
        """动态获取列索引"""
        config = sheet_type.value
        try:
            return config.headers.index(header) + 1  # Excel列从1开始
        except ValueError:
            raise KeyError(f"列'{header}'不存在于工作表{config.name}")

    def add_project_artifact(self, artifact_type: str, version: str, file_path: str):
        """记录项目产物"""
        ws = self.wb[SheetType.VERSION_HISTORY.value.name]
        cols = SheetType.VERSION_HISTORY.value.columns
        
        ws.append([
            version,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(file_path),
            artifact_type,
            "产物生成",
            f"新增{artifact_type}产物: {version}",
            ""
        ])
        self.wb.save(self.file_path)

    def get_version_history(self, doc_type: str = None) -> List[dict]:
        """获取版本历史"""
        ws = self.wb[SheetType.VERSION_HISTORY.value.name]
        cols = SheetType.VERSION_HISTORY.value.columns
        
        history = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            record = {
                "version": row[cols.VERSION.value-1],  # values_only=True返回元组，索引从0开始
                "time": row[cols.GEN_TIME.value-1],
                "doc_path": row[cols.DOC_PATH.value-1],
                "doc_type": row[cols.DOC_TYPE.value-1],
                "changes": row[cols.CHANGES.value-1].split("\n") if row[cols.CHANGES.value-1] else [],
                "related_reqs": row[cols.RELATED_REQS.value-1].split(",") if row[cols.RELATED_REQS.value-1] else []
            }
            if not doc_type or doc_type == record["doc_type"]:
                history.append(record)
        return sorted(history, key=lambda x: x["time"], reverse=True)

