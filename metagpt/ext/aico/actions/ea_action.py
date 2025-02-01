#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : ea_action.py
"""
from typing import Dict
from metagpt.actions import Action

ASSESSMENT_PROMPT = """
你是一位企业架构师,请对需求进行4A架构评估。评估结果需要包含以下内容:

1. 引言
   - 项目背景
   - 目标与范围
   - 方法论与参考标准(TOGAF/BPMN等)

2. 业务架构(BA)
   - 企业战略概述
   - 业务能力模型
   - 组织结构与角色职责
   - 业务流程分析(使用mermaid sequenceDiagram)

3. 应用架构(AA)
   - 应用系统全景
   - 应用功能分布
   - 应用间集成关系
   - 应用部署策略

4. 数据架构(DA)
   - 数据主题域
   - 核心数据实体
   - 数据流向图
   - 数据标准规范

5. 技术架构(TA)
   - 技术平台选型
   - 部署架构设计
   - 安全架构设计
   - 性能与扩展性

需求信息:
{requirements}

请进行分析并返回JSON格式的4A评估结果,包含上述所有章节。对于流程图和架构图,使用mermaid语法描述。
"""

ARCH_DESIGN_PROMPT = """
你是一位企业架构师,请根据4A评估结果编写详细的架构设计文档。文档需要包含:

1. 引言
   - 项目背景
   - 目标与范围
   - 方法论与参考标准

2. 业务架构
   - 企业战略概述
   - 业务能力模型
   - 组织结构与角色职责
   - 业务流程分析(使用mermaid sequenceDiagram)

3. 详细设计方案
   - 系统拓扑图(使用mermaid graph)
   - 模块划分
   - 接口定义
   - 数据模型
   - 部署方案

4. 关键技术说明
   - 技术选型说明
   - 框架使用说明
   - 开发规范说明

5. 安全性设计
   - 安全架构
   - 安全策略
   - 安全实现

6. 整体评估与后续规划
   - 整体评估
   - 后续规划
   - 最终建议

4A评估结果:
{assessment}

请编写架构设计文档并以JSON格式返回,确保包含上述所有章节。对于流程图和架构图,使用mermaid语法描述。
"""

class Conduct4AAssessment(Action):
    """进行4A架构评估"""
    
    async def run(self, requirements: Dict) -> Dict:
        prompt = ASSESSMENT_PROMPT.format(requirements=requirements)
        assessment = await self.llm.aask(prompt)
        return assessment

class WriteArchitectureDesign(Action):
    """编写架构设计文档"""
    
    async def run(self, assessment: Dict) -> Dict:
        prompt = ARCH_DESIGN_PROMPT.format(assessment=assessment)
        design = await self.llm.aask(prompt)
        return design 