from pathlib import Path
from openpyxl import load_workbook, Workbook
from datetime import datetime
from enum import Enum
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

from .tracking_service_factory import TrackingServiceFactory
from metagpt.ext.aico.config.tracking_config import SheetType
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

@dataclass
class TrackingServiceConfig:
    file_path: Path
    env: str = "prod"

class ProjectTrackingService:
    """项目跟踪服务（封装所有Excel操作）"""
    
    def __init__(self, config: TrackingServiceConfig):
        self.service = TrackingServiceFactory.create(
            config.file_path, 
            config.env
        )
        
    def __getattr__(self, name):
        """代理所有方法调用到具体服务"""
        return getattr(self.service, name)

    def _get_workbook(self) -> Workbook:
        """获取工作簿（带缓存）"""
        return self.service._get_workbook()
    
    def _create_new_tracking_file(self):
        """创建新跟踪文件"""
        self.service._create_new_tracking_file()
        
    def _init_sheets(self):
        """初始化所有工作表"""
        self.service._init_sheets()
    
    def save(self):
        """保存变更"""
        self.service.save()
                
    def close(self):
        """释放资源"""
        self.service.close()
            
    # 原始需求表操作 --------------------------------------------------
    def get_raw_requirement_status(self, file_path: str) -> Optional[Dict]:
        """获取原始需求状态"""
        return self.service.get_raw_requirement_status(file_path)
        
    def update_raw_requirement_status(
        self, 
        file_path: str, 
        status: str,
        update_time: datetime = datetime.now()
    ):
        """更新原始需求状态"""
        return self.service.update_raw_requirement_status(file_path, status, update_time)
    
    # 需求管理表操作 --------------------------------------------------
    def add_requirement(
        self,
        req_id: str,
        raw_file: str,
        req_data: Dict,
        output_files: List[str]
    ):
        """添加标准需求记录"""
        self.service.add_requirement(req_id, raw_file, req_data, output_files)
    
    # 用户故事管理操作 --------------------------------------------------
    def add_user_stories(self, biz_req_id: str, stories: List[Dict]):
        """批量添加用户故事"""
        self.service.add_user_stories(biz_req_id, stories)

    def add_task(self, task_data: dict):
        """添加任务记录"""
        self.service.add_task(task_data)

    def update_task_status(self, task_id: str, status: str, update_time: datetime = datetime.now()):
        """更新任务状态"""
        return self.service.update_task_status(task_id, status, update_time)

    def add_raw_requirement(
        self,
        file_path: str,
        req_type: str,
        status: str = "待分析",
        comment: str = ""
    ):
        """添加原始需求记录"""
        self.service.add_raw_requirement(file_path, req_type, status, comment)
        
    def get_pending_requirements(self) -> List[dict]:
        """获取待分析需求"""
        return self.service.get_pending_requirements()
    
    def update_requirement_status(self, req_id: str, status: str):
        """更新需求状态"""
        return self.service.update_requirement_status(req_id, status)

    def validate_file_structure(self) -> bool:
        """校验文件结构完整性"""
        return self.service.validate_file_structure()

    def update_requirement(self, req_id: str, **kwargs):
        """更新需求信息"""
        return self.service.update_requirement(req_id, **kwargs)

    def _get_column_index(self, sheet_type: SheetType, header: str) -> int:
        """动态获取列索引"""
        config = sheet_type.value
        try:
            return config.headers.index(header) + 1  # Excel列从1开始
        except ValueError:
            raise KeyError(f"列'{header}'不存在于工作表{config.name}")

# 兼容旧版初始化方式
def create_service(file_path: Path) -> ProjectTrackingService:
    return ProjectTrackingService(
        TrackingServiceConfig(file_path=file_path)
    ) 