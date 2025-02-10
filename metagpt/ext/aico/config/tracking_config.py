from enum import Enum
from dataclasses import dataclass

@dataclass
class SheetConfig:
    name: str
    headers: list
    columns: Enum  # 添加columns字段

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
    DESIGN_STATUS = 12    # 新增设计状态字段
    DESIGN_DOC = 13       # 新增设计文档字段
    CODE_BASELINE = 14    # 新增代码基线字段
    DESIGN_REVIEW = 15    # 新增设计评审字段
    REQ_NOTES = 16       # 备注

class UserStoryColumns(Enum):
    """用户故事表列定义"""
    STORY_ID = 1         # 用户故事ID
    RELATED_REQ_ID = 2   # 关联需求ID
    STORY_NAME = 3       # 用户故事名称
    STORY_DESC = 4       # 用户故事描述
    STORY_PRIORITY = 5   # 优先级
    STATUS = 6           # 状态（修正字段名）
    STORY_ACCEPTANCE = 7 # 验收标准
    CREATE_TIME = 8      # 创建时间
    STORY_NOTES = 9      # 备注

class TaskTrackingColumns(Enum):
    """任务跟踪表列定义"""
    TASK_ID = 1          # 任务ID
    RELATED_REQ_ID = 2   # 关联需求ID
    RELATED_STORY_ID =3  # 关联用户故事ID
    TASK_NAME = 4        # 任务名称
    TASK_DESC = 5        # 任务描述
    TASK_TYPE = 6        # 任务类型
    OWNER = 7            # 负责人
    STATUS = 8           # 任务状态
    PLAN_START = 9       # 计划开始时间
    PLAN_END = 10        # 计划结束时间
    ACTUAL_START = 11    # 实际开始时间
    ACTUAL_END = 12      # 实际结束时间
    ARTIFACTS = 13       # 关联产出物
    NOTES = 14           # 备注

class SheetType(Enum):
    RAW_REQUIREMENT = SheetConfig(
        name="原始需求",
        headers=["需求文件", "需求类型", "添加时间", "当前状态", "关联需求ID", 
                "BA解析时间", "EA解析时间", "完成时间", "备注"],
        columns=RawReqColumns
    )
    REQUIREMENT_MGMT = SheetConfig(
        name="需求管理",
        headers=[
            "需求ID", "原始需求文件", "需求名称", "需求描述", "需求来源",
            "需求优先级", "需求状态", "提出人/负责人", "提出时间", "目标完成时间",
            "验收标准", "设计状态", "关联设计文档", "代码基线版本", "设计评审记录", "备注"
        ],
        columns=ReqMgmtColumns
    )
    USER_STORY = SheetConfig(
        name="用户故事管理",
        headers=["用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述",
                "优先级", "状态", "验收标准", "创建时间", "备注"],
        columns=UserStoryColumns
    )
    TASK_TRACKING = SheetConfig(
        name="任务跟踪",
        headers=[
            "任务ID", "关联需求ID", "关联用户故事ID", "任务名称", "任务描述",
            "任务类型", "负责人", "任务状态", "计划开始时间", "计划结束时间",
            "实际开始时间", "实际结束时间", "关联产出物", "备注"
        ],
        columns=TaskTrackingColumns
    )

    @classmethod
    def get_required_sheets(cls):
        """动态获取所有工作表配置"""
        return [member.value for member in cls] 

class IDConfig:
    """ID生成配置"""
    DEFAULT_PRIORITY = "中"  # 新增默认优先级
    PROJECT_PREFIX = "PM"
    TASK_TYPES = {
        "dev": "DEV",
        "test": "TEST",
        "design": "DESIGN",
        # 补充其他任务类型
    }
    REQUIREMENT_SEQ_LENGTH = 3  # 序列号位数
    YEAR_FORMAT = "%y"          # 年份格式(24)
    MONTH_FORMAT = "%m"         # 月份格式(07)
    USER_STORY_SEQ_LENGTH = 2   # 用户故事子编号位数
    TASK_SEQ_LENGTH = 2         # 任务序号位数 