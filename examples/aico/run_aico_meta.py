#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : run_aico_meta.py
说明:
  AICO项目启动入口:
  1. 支持多种原始需求输入(文件、文本、视频等)
  2. 项目初始化由PM角色负责
  3. 提供项目基本信息配置
"""
import asyncio
from pathlib import Path
import typer
import json
from typing import Dict, Optional

from metagpt.config2 import config
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.ext.aico.roles.project_manager import AICOProjectManager
from metagpt.ext.aico.roles.business_analyst import AICOBusinessAnalyst
from metagpt.ext.aico.roles.enterprise_architect import AICOEnterpriseArchitect
from metagpt.team import Team

app = typer.Typer(add_completion=False)

def load_raw_requirement(req_path: str) -> str:
    """加载原始需求文件
    
    支持多种格式:
    - Markdown文档(.md)
    - Word文档(.docx)
    - 文本文件(.txt)
    - 视频文件(.mp4)等
    """
    req_file = Path(req_path)
    if not req_file.exists():
        raise FileNotFoundError(f"需求文件不存在: {req_path}")
        
    # 根据文件类型处理
    if req_file.suffix == '.md':
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    elif req_file.suffix == '.txt':
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        # 其他格式文件,返回文件路径,由角色自行处理
        content = str(req_file)
        
    return content

@app.command()
def run_aico(
    raw_requirement: str = typer.Argument(
        ..., 
        help="原始需求输入,可以是文件路径或直接的需求文本"
    ),
    project_name: str = typer.Option(
        "aico-demo",
        help="项目名称"
    ),
    output_root: str = typer.Option(
        "output",
        help="输出目录"
    ),
    investment: float = typer.Option(
        default=10.0,
        help="投资金额"
    ),
    n_round: int = typer.Option(
        default=5,
        help="最大对话轮数"
    )
):
    """运行AICO项目
    
    支持:
    1. 文件输入: python run_aico_meta.py docs/requirements.md
    2. 文本输入: python run_aico_meta.py "这是一段需求描述..."
    """
    # 处理原始需求输入
    try:
        # 尝试作为文件路径加载
        requirement = load_raw_requirement(raw_requirement)
    except FileNotFoundError:
        # 不是文件路径,则作为直接的需求文本
        requirement = raw_requirement
    
    # 初始化环境
    env = AICOEnvironment()
    
    # 创建团队
    team = Team(env=env)
    
    # 配置项目信息
    project_info = {
        "name": project_name,
        "output_root": output_root,
        "raw_requirement": requirement
    }
    
    # 雇佣角色(PM负责项目初始化)
    team.hire([
        AICOProjectManager(
            project_info=project_info
        ),
        AICOBusinessAnalyst(),
        AICOEnterpriseArchitect()
    ])
    
    # 投资项目
    team.invest(investment)
    
    # 启动项目
    team.run_project(
        idea=requirement,  # 原始需求
        project_info=project_info  # 项目信息
    )
    
    # 运行对话
    asyncio.run(team.run(n_round=n_round))

if __name__ == "__main__":
    app()
