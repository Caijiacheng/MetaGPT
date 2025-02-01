#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : pm_action.py
"""
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from openpyxl import Workbook, load_workbook
import logging

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

原始需求:
{idea}

请解析并返回JSON格式的结果,包含上述所有字段。
"""

DATA_MIGRATION_PROMPT = """
你是一个数据迁移专家。请分析源Excel文件的结构,生成到目标格式的迁移方案。

源Excel文件结构:
{source_structure}

目标格式要求:
1. 需求管理表字段:
{req_fields}

2. 用户故事管理表字段:
{story_fields}

请生成Python代码,实现数据迁移。要求:
1. 使用openpyxl库
2. 保留原有数据的关联关系
3. 对缺失字段填充默认值
4. 确保ID格式符合规范
5. 处理可能的数据冲突

注意:
- 需求ID格式: REQ-XXX
- 用户故事ID格式: US-XXX
- 时间格式: YYYY-MM-DD HH:mm:ss
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
    """准备项目文档"""
    
    REQUIRED_SHEETS = {
        "需求管理": [
            "需求ID", "需求名称", "需求描述", "需求来源", 
            "优先级", "状态", "提出人", "提出时间",
            "目标完成时间", "验收标准", "备注"
        ],
        "用户故事管理": [
            "故事ID", "关联需求ID", "故事名称", "故事描述",
            "优先级", "状态", "验收标准", "创建时间", "备注"
        ]
    }
    
    def _validate_excel_format(self, wb) -> bool:
        """验证Excel格式是否符合规范"""
        # 检查sheet是否存在
        if not all(sheet in wb.sheetnames for sheet in self.REQUIRED_SHEETS):
            return False
            
        # 检查每个sheet的表头
        for sheet_name, required_headers in self.REQUIRED_SHEETS.items():
            ws = wb[sheet_name]
            headers = [cell.value for cell in ws[1]]
            if not all(header in headers for header in required_headers):
                return False
                
        return True
        
    def _create_standard_excel(self, file_path: Path):
        """创建标准格式的Excel文件"""
        wb = Workbook()
        
        # 创建并配置每个sheet
        for sheet_name, headers in self.REQUIRED_SHEETS.items():
            if sheet_name == "需求管理":
                ws = wb.active
                ws.title = sheet_name
            else:
                ws = wb.create_sheet(sheet_name)
            ws.append(headers)
            
        wb.save(file_path)
        return wb
        
    def _get_excel_structure(self, wb) -> Dict:
        """获取Excel文件结构"""
        structure = {}
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            headers = [cell.value for cell in ws[1]]
            data_sample = []
            for row in ws.iter_rows(min_row=2, max_row=3):
                data_sample.append([cell.value for cell in row])
            structure[sheet_name] = {
                "headers": headers,
                "data_sample": data_sample
            }
        return structure
    
    async def _migrate_data(self, old_wb, new_wb):
        """使用LLM生成并执行数据迁移脚本"""
        try:
            # 获取源文件结构
            source_structure = self._get_excel_structure(old_wb)
            
            # 生成迁移脚本
            prompt = DATA_MIGRATION_PROMPT.format(
                source_structure=source_structure,
                req_fields="\n".join(f"- {f}" for f in self.REQUIRED_SHEETS["需求管理"]),
                story_fields="\n".join(f"- {f}" for f in self.REQUIRED_SHEETS["用户故事管理"])
            )
            
            migration_code = await self.llm.aask(prompt)
            
            # 执行迁移脚本
            local_vars = {
                "old_wb": old_wb,
                "new_wb": new_wb,
                "datetime": datetime
            }
            exec(migration_code, globals(), local_vars)
            
            return True
            
        except Exception as e:
            logging.error(f"数据迁移失败: {str(e)}")
            logging.error("需要人工处理数据迁移")
            
            # 保存原文件的备份
            backup_path = self.env.tracking_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            old_wb.save(backup_path)
            
            # 记录迁移失败信息
            error_log = self.env.tracking_root / "migration_error.log"
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] 迁移失败\n")
                f.write(f"错误信息: {str(e)}\n")
                f.write(f"原文件备份: {backup_path}\n")
                f.write("源文件结构:\n")
                f.write(str(source_structure))
                f.write("\n\n")
            
            return False
    
    async def run(self, idea: str, root_dir: Path) -> Dict:
        # 生成项目名称
        project_name = f"AICO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 初始化环境
        self.env.init_project(project_name, root_dir)
        
        # 获取需求跟踪文件路径
        req_file = self.env.get_tracking_file("requirements")
        
        # 检查文件是否存在
        if req_file.exists():
            try:
                wb = load_workbook(req_file)
                if not self._validate_excel_format(wb):
                    # 格式不符合规范,创建新文件并迁移数据
                    old_wb = wb
                    wb = self._create_standard_excel(req_file)
                    migration_success = await self._migrate_data(old_wb, wb)
                    if not migration_success:
                        # 迁移失败,使用新的空文件
                        wb = self._create_standard_excel(req_file)
            except Exception as e:
                # 文件损坏或无法读取,创建新文件
                wb = self._create_standard_excel(req_file)
        else:
            # 文件不存在,创建新文件
            wb = self._create_standard_excel(req_file)
            
        wb.save(req_file)
        
        return {
            "project_name": project_name,
            "idea": idea,
            "tracking_file": str(req_file)
        }

class ParseRequirements(Action):
    """解析需求"""
    
    def _get_next_req_id(self, ws) -> str:
        """获取下一个需求ID"""
        max_id = 0
        for row in ws.iter_rows(min_row=2):
            req_id = row[0].value
            if req_id and req_id.startswith("REQ-"):
                try:
                    num = int(req_id.split("-")[1])
                    max_id = max(max_id, num)
                except ValueError:
                    continue
        return f"REQ-{max_id + 1:03d}"
    
    async def run(self, project_info: Dict) -> Dict:
        # 使用LLM解析需求
        prompt = REQUIREMENT_PARSE_PROMPT.format(
            idea=project_info.get("idea", "")
        )
        requirements = await self.llm.aask(prompt)
        
        # 将解析结果写入Excel
        tracking_file = project_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["需求管理"]
            
            # 获取下一个需求ID
            next_req_id = self._get_next_req_id(ws)
            
            # 更新requirements中的ID
            requirements["需求ID"] = next_req_id
            
            # 添加新行
            ws.append([
                requirements.get(field, "") 
                for field in PrepareProject.REQUIRED_SHEETS["需求管理"]
            ])
            
            wb.save(tracking_file)
        
        return {
            "requirements": requirements,
            "tracking_file": tracking_file
        }

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