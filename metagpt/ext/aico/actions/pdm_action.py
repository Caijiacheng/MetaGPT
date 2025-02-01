from typing import Dict
from metagpt.actions import Action

PRD_PROMPT = """
你是一位产品经理,请根据需求编写PRD文档:

1. 产品概述
2. 功能需求
   - 功能描述
   - 业务规则
   - 界面原型
3. 非功能需求
   - 性能要求
   - 安全要求
   - 可用性要求
4. 验收标准

需求信息:
{requirements}

请编写PRD文档并以JSON格式返回。
"""

REVISE_PRD_PROMPT = """
你是一位产品经理,请根据架构设计结果修订PRD文档:

原PRD文档:
{prd}

架构设计:
{arch_design}

请修订PRD文档并以JSON格式返回修订后的内容。
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
        prompt = REVISE_PRD_PROMPT.format(
            prd=prd,
            arch_design=arch_design
        )
        revised_prd = await self.llm.aask(prompt)
        return revised_prd 