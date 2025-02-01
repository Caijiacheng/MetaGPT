from typing import Dict
from metagpt.actions import Action

PRD_PROMPT = """
你是一位产品经理，请根据以下需求编写PRD文档，输出JSON格式，要求包含：
{
  "product_overview": "产品概述",
  "functional_requirements": [{"feature": "功能描述", "business_rules": "业务规则", "ui_prototype": "界面原型"}],
  "non_functional_requirements": {"performance": "性能要求", "security": "安全要求", "usability": "可用性要求"},
  "acceptance_criteria": "验收标准"
}

需求信息:
{requirements}
"""

REVISE_PRD_PROMPT = """
你是一位产品经理，请根据以下架构设计结果修订PRD文档，输出JSON格式，要求包含与原文档一致的所有字段，并进行必要的更新：
{
  "product_overview": "产品概述",
  "functional_requirements": [...],
  "non_functional_requirements": {...},
  "acceptance_criteria": "修订后的验收标准"
}

原PRD文档:
{prd}

架构设计:
{arch_design}
"""

class WritePRD(Action):
    """编写PRD文档"""
    async def run(self, requirements: Dict) -> Dict:
        prompt = PRD_PROMPT.format(requirements=requirements)
        prd = await self.llm.aask(prompt)
        return prd

class RevisePRD(Action):
    """修订PRD文档"""
    async def run(self, prd: Dict, arch_design: Dict) -> Dict:
        prompt = REVISE_PRD_PROMPT.format(prd=prd, arch_design=arch_design)
        revised_prd = await self.llm.aask(prompt)
        return revised_prd 