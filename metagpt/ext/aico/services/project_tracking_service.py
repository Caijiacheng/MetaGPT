from pathlib import Path
from openpyxl import load_workbook, Workbook
from datetime import datetime
from enum import Enum
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class TrackingSheet(Enum):
    """跟踪表工作表定义"""
    RAW_REQUIREMENTS = "原始需求"
    REQUIREMENT_MGMT = "需求管理"
    USER_STORY_MGMT = "用户故事管理"
    TASK_TRACKING = "任务跟踪"

class ColumnIndex:
    """列索引常量（根据project_tracking_spec.md）"""
    # 原始需求表
    RAW_FILE_PATH = 1    # 需求文件
    REQ_TYPE = 2         # 需求类型
    ADD_TIME = 3         # 添加时间
    STATUS = 4           # 当前状态
    RELATED_REQ_ID = 5   # 关联需求ID
    BA_PARSE_TIME = 6    # BA解析时间
    EA_PARSE_TIME = 7    # EA解析时间
    COMPLETE_TIME = 8     # 完成时间
    NOTES = 9            # 备注
    
    # 需求管理表
    REQ_ID = 1           # 需求ID
    RAW_FILE_REF = 2     # 原始需求文件
    REQ_NAME = 3         # 需求名称
    REQ_DESC = 4         # 需求描述
    REQ_SOURCE = 5       # 需求来源
    REQ_PRIORITY = 6     # 需求优先级
    REQ_STATUS = 7       # 需求状态
    REQ_OWNER = 8        # 提出人/负责人
    SUBMIT_TIME = 9      # 提出时间
    DUE_DATE = 10        # 目标完成时间
    ACCEPTANCE = 11      # 验收标准
    REQ_NOTES = 12       # 备注
    
    # 用户故事管理表
    STORY_ID = 1         # 用户故事ID
    RELATED_REQ_ID = 2   # 关联需求ID
    STORY_NAME = 3       # 用户故事名称
    STORY_DESC = 4       # 用户故事描述
    STORY_PRIORITY = 5   # 优先级
    STORY_STATUS = 6     # 状态
    STORY_ACCEPTANCE = 7 # 验收标准
    CREATE_TIME = 8      # 创建时间
    STORY_NOTES = 9      # 备注
    
    # 任务跟踪表
    TASK_ID = 1          # 任务ID
    TASK_RELATED_REQ = 2 # 关联需求ID
    TASK_RELATED_STORY =3# 关联用户故事ID
    TASK_NAME = 4        # 任务名称
    TASK_DESC = 5        # 任务描述
    TASK_TYPE = 6        # 任务类型
    TASK_OWNER = 7       # 负责人
    TASK_STATUS = 8      # 任务状态
    PLAN_START = 9       # 计划开始时间
    PLAN_END = 10        # 计划结束时间
    ACTUAL_START = 11    # 实际开始时间
    ACTUAL_END = 12      # 实际结束时间
    TASK_NOTES = 13      # 备注

class ProjectTrackingService:
    """项目跟踪服务（封装所有Excel操作）"""
    
    def __init__(self, tracking_file: Path):
        self.tracking_file = tracking_file
        self._wb = None
        
    def _get_workbook(self) -> Workbook:
        """获取工作簿（带缓存）"""
        if not self._wb:
            if self.tracking_file.exists():
                self._wb = load_workbook(self.tracking_file)
            else:
                self._create_new_tracking_file()
        return self._wb
    
    def _create_new_tracking_file(self):
        """创建新跟踪文件"""
        self._wb = Workbook()
        self._init_sheets()
        self.save()
        
    def _init_sheets(self):
        """初始化所有工作表"""
        # 删除默认sheet
        if 'Sheet' in self._wb.sheetnames:
            del self._wb['Sheet']
            
        # 创建规范的工作表
        sheets = {
            TrackingSheet.RAW_REQUIREMENTS: [
                "需求文件", "需求类型", "添加时间", "当前状态", 
                "关联需求ID", "BA解析时间", "EA解析时间", "完成时间", "备注"
            ],
            TrackingSheet.REQUIREMENT_MGMT: [
                "需求ID", "原始需求文件", "需求名称", "需求描述",
                "需求来源", "需求优先级", "需求状态", "提出人/负责人",
                "提出时间", "目标完成时间", "验收标准", "备注"
            ],
            TrackingSheet.USER_STORY_MGMT: [
                "用户故事ID", "关联需求ID", "用户故事名称",
                "用户故事描述", "优先级", "状态", 
                "验收标准", "创建时间", "备注"
            ],
            TrackingSheet.TASK_TRACKING: [
                "任务ID", "关联需求ID", "关联用户故事ID",
                "任务名称", "任务描述", "任务类型",
                "负责人", "任务状态", "计划开始时间",
                "计划结束时间", "实际开始时间", 
                "实际结束时间", "备注"
            ]
        }
        
        for sheet, headers in sheets.items():
            if sheet.value not in self._wb.sheetnames:
                ws = self._wb.create_sheet(sheet.value)
                ws.append(headers)
    
    def save(self):
        """保存变更"""
        if self._wb:
            try:
                self._wb.save(self.tracking_file)
            except PermissionError as e:
                logger.error(f"文件保存失败：{self.tracking_file} 可能被其他进程占用")
                raise
                
    def close(self):
        """释放资源"""
        if self._wb:
            self._wb.close()
            self._wb = None
            
    # 原始需求表操作 --------------------------------------------------
    def get_raw_requirement_status(self, file_path: str) -> Optional[Dict]:
        """获取原始需求状态"""
        ws = self._get_workbook()[TrackingSheet.RAW_REQUIREMENTS.value]
        for row in ws.iter_rows(min_row=2):
            if row[ColumnIndex.RAW_FILE_PATH - 1].value == file_path:
                return {
                    "status": row[ColumnIndex.STATUS - 1].value,
                    "ba_time": row[ColumnIndex.BA_PARSE_TIME - 1].value,
                    "ea_time": row[ColumnIndex.EA_PARSE_TIME - 1].value
                }
        return None
        
    def update_raw_requirement_status(
        self, 
        file_path: str, 
        status: str,
        update_time: datetime = datetime.now()
    ):
        """更新原始需求状态"""
        ws = self._get_workbook()[TrackingSheet.RAW_REQUIREMENTS.value]
        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            if row[ColumnIndex.RAW_FILE_PATH - 1].value == file_path:
                ws.cell(row=row_idx, column=ColumnIndex.STATUS, value=status)
                
                if status == "业务分析完成":
                    ws.cell(row=row_idx, column=ColumnIndex.BA_PARSE_TIME, value=update_time)
                elif status == "技术分析完成":
                    ws.cell(row=row_idx, column=ColumnIndex.EA_PARSE_TIME, value=update_time)
                elif status == "已完成":
                    ws.cell(row=row_idx, column=ColumnIndex.COMPLETE_TIME, value=update_time)
                return True
        return False
    
    # 需求管理表操作 --------------------------------------------------
    def add_requirement(
        self,
        req_id: str,
        raw_file: str,
        req_data: Dict,
        output_files: List[str]
    ):
        """添加标准需求记录"""
        ws = self._get_workbook()[TrackingSheet.REQUIREMENT_MGMT.value]
        new_row = [
            req_id,
            raw_file,
            req_data.get("name", ""),
            req_data.get("description", ""),
            req_data.get("source", "system"),
            req_data.get("priority", "P0"),
            "已基线化",
            req_data.get("owner", "系统"),
            datetime.now().isoformat(),
            req_data.get("due_date", ""),
            req_data.get("acceptance", ""),
            f"关联文件: {', '.join(output_files)}"
        ]
        ws.append(new_row)
    
    # 用户故事管理操作 --------------------------------------------------
    def add_user_stories(self, biz_req_id: str, stories: List[Dict]):
        """批量添加用户故事"""
        ws = self._get_workbook()[TrackingSheet.USER_STORY_MGMT.value]
        for story in stories:
            new_row = [
                f"US-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                biz_req_id,
                story.get("title", ""),
                story.get("description", ""),
                story.get("priority", "P0"),
                "待实现",
                story.get("acceptance", ""),
                datetime.now().isoformat(),
                story.get("comment", "")
            ]
            ws.append(new_row)

    def add_task(self, task_data: dict):
        """添加任务记录"""
        ws = self._get_workbook()[TrackingSheet.TASK_TRACKING.value]
        new_row = [
            task_data.get("task_id", f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            task_data.get("related_req_id", ""),
            task_data.get("related_story_id", ""),
            task_data.get("name", ""),
            task_data.get("description", ""),
            task_data.get("type", "开发"),
            task_data.get("owner", "未分配"),
            task_data.get("status", "待开始"),
            task_data.get("plan_start", ""),
            task_data.get("plan_end", ""),
            task_data.get("actual_start", ""),
            task_data.get("actual_end", ""),
            task_data.get("notes", "")
        ]
        ws.append(new_row)

    def update_task_status(self, task_id: str, status: str, update_time: datetime = datetime.now()):
        """更新任务状态"""
        ws = self._get_workbook()[TrackingSheet.TASK_TRACKING.value]
        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            if row[ColumnIndex.TASK_ID - 1].value == task_id:
                ws.cell(row=row_idx, column=ColumnIndex.TASK_STATUS, value=status)
                if status == "进行中":
                    ws.cell(row=row_idx, column=ColumnIndex.ACTUAL_START, value=update_time)
                elif status == "已完成":
                    ws.cell(row=row_idx, column=ColumnIndex.ACTUAL_END, value=update_time)
                return True
        return False 