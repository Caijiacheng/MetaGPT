from pathlib import Path
from datetime import datetime
from typing import Dict, List
from openpyxl import Workbook
from metagpt.actions import Action

REQUIREMENT_PARSE_PROMPT = """
你是一个需求分析专家。请按照以下AICO规范解析用户需求：

1. 需求管理表字段：
- 需求ID (REQ-XXX格式)
- 需求名称
- 需求描述
- 需求来源
- 需求优先级 (高/中/低)
- 需求状态
- 提出人
- 提出时间
- 目标完成时间
- 验收标准
- 备注

2. 用户故事管理表字段：
- 用户故事ID (US-XXX格式)
- 关联需求ID
- 用户故事名称
- 用户故事描述 (作为...角色，我想要...，以便...)
- 优先级
- 状态
- 验收标准
- 创建时间
- 备注

原始需求:
{raw_requirements}

请解析并返回JSON格式的结果，包含requirements和user_stories两个数组。
"""

TASK_BREAKDOWN_PROMPT = """
你是一个项目管理专家。请根据以下需求和用户故事，按AICO规范拆解具体任务：

任务跟踪表字段：
- 任务ID (T-XXX格式)
- 关联需求ID
- 关联用户故事ID
- 任务名称
- 任务描述
- 任务类型 (开发/测试/设计/文档等)
- 负责人
- 任务状态
- 计划开始时间
- 计划结束时间
- 实际开始时间
- 实际结束时间
- 备注

需求和用户故事:
{requirements_and_stories}

请拆解并返回JSON格式的任务列表。每个用户故事至少应该包含开发任务和测试任务。
"""

class PrepareProject(Action):
    """按AICO规范初始化项目文档"""
    
    async def run(self, project_name: str, scope: str) -> Dict:
        base_dir = Path(f"projects/{project_name}")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化ReqTracking.xlsx
        req_wb = Workbook()
        req_ws = req_wb.active
        req_ws.title = "需求管理"
        req_ws.append([
            "需求ID", "需求名称", "需求描述", "需求来源", 
            "需求优先级", "需求状态", "提出人", "提出时间",
            "目标完成时间", "验收标准", "备注"
        ])
        
        # 创建用户故事sheet
        story_ws = req_wb.create_sheet("用户故事管理")
        story_ws.append([
            "用户故事ID", "关联需求ID", "用户故事名称", "用户故事描述",
            "优先级", "状态", "验收标准", "创建时间", "备注"
        ])
        
        req_wb.save(base_dir / "ReqTracking.xlsx")
        
        # 初始化TaskTracking.xlsx
        task_wb = Workbook()
        task_ws = task_wb.active
        task_ws.append([
            "任务ID", "关联需求ID", "关联用户故事ID", "任务名称", 
            "任务描述", "任务类型", "负责人", "任务状态",
            "计划开始时间", "计划结束时间", "实际开始时间", 
            "实际结束时间", "备注"
        ])
        task_wb.save(base_dir / "TaskTracking.xlsx")
        
        return {
            "project_name": project_name,
            "scope": scope,
            "doc_paths": {
                "requirements": str(base_dir / "ReqTracking.xlsx"),
                "tasks": str(base_dir / "TaskTracking.xlsx")
            }
        }

class ParseRequirements(Action):
    """解析原始需求为AICO规范格式"""
    
    async def run(self, raw_requirements: str) -> Dict:
        prompt = REQUIREMENT_PARSE_PROMPT.format(
            raw_requirements=raw_requirements
        )
        # 调用AI引擎解析需求
        parsed_result = await self.llm.aask(prompt)
        return parsed_result

class BreakDownTasks(Action):
    """将需求和用户故事拆解为具体任务"""
    
    async def run(self, requirements_and_stories: Dict) -> List[Dict]:
        prompt = TASK_BREAKDOWN_PROMPT.format(
            requirements_and_stories=requirements_and_stories
        )
        # 调用AI引擎拆解任务
        tasks = await self.llm.aask(prompt)      
        return tasks

class UpdateTaskStatus(Action):
    """更新任务状态"""
    
    async def run(self, task_id: str, new_status: str) -> Dict:
        return {
            "task_id": task_id,
            "status": new_status,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        } 