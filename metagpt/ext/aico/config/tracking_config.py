from enum import Enum
from dataclasses import dataclass

@dataclass
class SheetConfig:
    name: str
    headers: list[str]
    col_count: int

class SheetType(Enum):
    RAW_REQUIREMENT = SheetConfig(
        name="原始需求",
        headers=[
            "需求文件", "需求类型", "添加时间", "当前状态",
            "关联需求ID", "BA解析时间", "EA解析时间", "完成时间", "备注"
        ],
        col_count=9
    )
    REQUIREMENT_MGMT = SheetConfig(
        name="需求管理",
        headers=[
            "需求ID", "原始需求文件", "需求名称", "需求描述",
            "需求来源", "需求优先级", "需求状态", "提出人/负责人",
            "提出时间", "目标完成时间", "验收标准", "备注"
        ],
        col_count=12
    )
    USER_STORY = SheetConfig(
        name="用户故事管理",
        headers=[
            "用户故事ID", "关联需求ID", "用户故事名称",
            "用户故事描述", "优先级", "状态", 
            "验收标准", "创建时间", "备注"
        ],
        col_count=9
    )
    TASK_TRACKING = SheetConfig(
        name="任务跟踪",
        headers=[
            "任务ID", "关联需求ID", "关联用户故事ID",
            "任务名称", "任务描述", "任务类型",
            "负责人", "任务状态", "计划开始时间",
            "计划结束时间", "实际开始时间", 
            "实际结束时间", "备注"
        ],
        col_count=13
    ) 