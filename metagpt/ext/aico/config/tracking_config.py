from enum import Enum
from dataclasses import dataclass

@dataclass
class SheetConfig:
    name: str
    headers: list[str]
    
    # 新增动态列索引生成
    @property
    def columns(self) -> Enum:
        """动态生成列名枚举"""
        return Enum(f"{self.name}Columns", {h: i+1 for i, h in enumerate(self.headers)}, type=int)

class RawReqColumns(Enum):
    """原始需求表列定义"""
    RAW_FILE_PATH = 1    # 需求文件
    REQ_TYPE = 2         # 需求类型
    ADD_TIME = 3         # 添加时间
    STATUS = 4           # 当前状态
    RELATED_REQ_ID = 5   # 关联需求ID
    BA_PARSE_TIME = 6    # BA解析时间
    EA_PARSE_TIME = 7    # EA解析时间
    COMPLETE_TIME = 8    # 完成时间
    NOTES = 9            # 备注

class ReqMgmtColumns(Enum):
    """需求管理表列定义"""
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

class UserStoryColumns(Enum):
    """用户故事表列定义"""
    STORY_ID = 1         # 用户故事ID
    RELATED_REQ_ID = 2   # 关联需求ID
    STORY_NAME = 3       # 用户故事名称
    STORY_DESC = 4       # 用户故事描述
    STORY_PRIORITY = 5   # 优先级
    STORY_STATUS = 6     # 状态
    STORY_ACCEPTANCE = 7 # 验收标准
    CREATE_TIME = 8      # 创建时间
    STORY_NOTES = 9      # 备注

class TaskTrackingColumns(Enum):
    """任务跟踪表列定义"""
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


class SheetType(Enum):
    RAW_REQUIREMENT = SheetConfig(
        name="原始需求",
        headers=[c.name for c in RawReqColumns],
        columns=RawReqColumns
    )
    REQUIREMENT_MGMT = SheetConfig(
        name="需求管理",
        headers=[c.name for c in ReqMgmtColumns],
        columns=ReqMgmtColumns
    )
    USER_STORY = SheetConfig(
        name="用户故事管理",
        headers=[c.name for c in UserStoryColumns],
        columns=UserStoryColumns
    )
    TASK_TRACKING = SheetConfig(
        name="任务跟踪",
        headers=[c.name for c in TaskTrackingColumns],
        columns=TaskTrackingColumns
    )


    @classmethod
    def get_required_sheets(cls):
        """动态获取所有工作表配置"""
        return [member.value for member in cls] 