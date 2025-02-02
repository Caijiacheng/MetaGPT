#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ea_action.py
@Modified By: Jiacheng Cai, 2023/12/15
说明:
  EA角色的核心动作包括:
  1. parseTechRequirements: 调用AI引擎分析技术需求,生成需求矩阵
  2. update4ATech: 调用AI引擎更新4A架构(应用架构、数据架构、技术架构)
"""
from typing import Dict
from datetime import datetime
from openpyxl import load_workbook
from metagpt.actions import Action
import json
from pathlib import Path

PARSE_TECH_REQUIREMENT_PROMPT = """
你是一位企业架构师,请调用AI引擎对以下架构文档进行分析,提取技术需求并输出需求矩阵,要求包含:
{
    "requirement_id": "TREQ-XXX",
    "type": "技术需求",
    "title": "需求标题",
    "description": "需求描述",
    "priority": "高/中/低",
    "status": "新建/分析中/已完成",
    "stakeholders": ["相关干系人"],
    "technical_value": "技术价值说明",
    "constraints": "约束条件",
    "dependencies": ["依赖的其他需求ID"],
    "created_time": "YYYY-MM-DD HH:mm:ss"
}

架构文档:
{requirements}
"""

UPDATE_4A_TECH_PROMPT = '''
请严格遵循《技术架构设计规范》中的以下要求：

【版本管理】
{version_rule}

【数据架构要求】
{data_arch_rule}

【技术选型规则】
{tech_selection_rule}

根据需求生成架构设计：
'''

ARCH_REFERENCE_PATH = Path("docs/aico/specs/EA-Design.md")

class ParseTechRequirements(Action):
    """调用AI引擎分析技术需求,生成需求矩阵"""
    async def run(self, requirements_info: Dict) -> Dict:
        # 调用AI引擎分析需求
        prompt = PARSE_TECH_REQUIREMENT_PROMPT.format(
            requirements=requirements_info.get("requirements", "")
        )
        requirement_matrix = await self.llm.aask(prompt)
        
        # 写入需求跟踪表
        tracking_file = requirements_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["需求管理"]
            
            # 解析需求矩阵并写入Excel
            matrix_data = json.loads(requirement_matrix)
            row = [
                matrix_data["requirement_id"],
                matrix_data["title"],
                matrix_data["description"],
                "技术需求",  # 需求来源
                matrix_data["priority"],
                matrix_data["status"],
                matrix_data["stakeholders"][0],  # 提出人取第一个干系人
                matrix_data["created_time"],
                "",  # 目标完成时间待定
                matrix_data.get("acceptance_criteria", ""),
                matrix_data.get("constraints", "")  # 约束作为备注
            ]
            ws.append(row)
            wb.save(tracking_file)
            
        return {
            "requirement_matrix": requirement_matrix,
            "tracking_file": tracking_file
        }

class Update4ATech(Action):
    """调用AI引擎更新4A架构"""
    async def run(self, requirement_info: Dict) -> Dict:
        # 加载技术架构参考
        with open(ARCH_REFERENCE_PATH, "r", encoding="utf-8") as f:
            tech_ref = "\n".join([
                line for line in f.readlines() 
                if "## 5. 技术架构（TA）" in line or line.startswith("### 5.")
            ])
            
        prompt = UPDATE_4A_TECH_PROMPT.format(
            tech_arch_ref=tech_ref,
            requirement_matrix=json.dumps(requirement_info, indent=2)
        )
        architecture_result = await self.llm.aask(prompt)
        
        # 写入架构设计文档
        tracking_file = requirement_info.get("tracking_file")
        if tracking_file:
            wb = load_workbook(tracking_file)
            ws = wb["架构设计"]
            # 写入架构设计
            # ws.append([...])  # 具体实现略
            wb.save(tracking_file)
            
        return {
            "4a_architecture": architecture_result.get("4a_architecture"),
            "tracking_file": tracking_file
        }

    async def _run_impl(self, input_data: Dict) -> Dict:
        # 加载业务架构和技术需求
        biz_arch = input_data["business_arch"]
        tech_req = input_data["requirement_matrix"]
        
        # 生成架构提示词
        prompt = f"""
        根据以下业务架构和技术需求，更新4A技术架构：
        
        【业务架构】
        {json.dumps(biz_arch, indent=2)}
        
        【技术需求】
        {json.dumps(tech_req, indent=2)}
        
        输出要求：
        1. 应用架构需支持业务架构中的{', '.join(biz_arch.get('processes', []))}流程
        2. 数据架构需包含{biz_arch.get('data_entities', [])}实体
        3. 技术架构需满足{tech_req.get('non_functional', '')}非功能需求
        """
        
        # 调用AI生成架构
        result = await self.llm.aask(prompt)
        return self._parse_arch(result)
        
    def _parse_arch(self, raw: str) -> Dict:
        try:
            data = json.loads(raw)
            # 强制字段检查
            assert "application_architecture" in data
            assert "services" in data["application_architecture"]
            return data
        except (json.JSONDecodeError, AssertionError) as e:
            self.logger.error(f"架构解析失败: {str(e)}")
            return self._generate_fallback_output()
            
    def _generate_fallback_output(self):
        """生成符合规范的空结构"""
        return {
            "application_architecture": {"services": [], "interfaces": []},
            "technical_architecture": {"deployment": "", "infrastructure": []},
            "data_architecture": {"models": [], "data_flow": ""},
            "security_architecture": {"access_control": ""}
        }

        # 写入任务跟踪表
        tracking_file = Path(input_data["tracking_file"])
        wb = load_workbook(tracking_file)
        if "任务跟踪" not in wb.sheetnames:
            task_sheet = wb.create_sheet("任务跟踪")
            task_sheet.append([
                "任务ID", "关联需求ID", "关联用户故事ID", "任务名称",
                "任务描述", "任务类型", "负责人", "任务状态",
                "计划开始时间", "计划结束时间", "实际开始时间", "实际结束时间", "备注"
            ])
        else:
            task_sheet = wb["任务跟踪"]
            
        # 生成架构相关任务
        task_sheet.append([
            f"T-{len(task_sheet.rows):03d}",
            input_data["requirement_id"],
            "ARCH-DESIGN",  # 特殊标记架构设计任务
            "4A架构设计评审",
            "完成技术架构设计评审",
            "架构设计",
            "EA系统",
            "已完成",
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            "关联架构文档：" + ARCH_REFERENCE_PATH.name
        ])
        wb.save(tracking_file) 