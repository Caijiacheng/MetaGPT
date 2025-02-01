#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : run_aico_meta.py
"""
import asyncio
from pathlib import Path
import typer

from metagpt.config2 import config
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.ext.aico.roles.project_manager import AICOProjectManager
from metagpt.ext.aico.roles.business_analyst import AICOBusinessAnalyst
from metagpt.ext.aico.roles.product_manager import AICOProductManager
from metagpt.ext.aico.roles.enterprise_architect import AICOEnterpriseArchitect
from metagpt.ext.aico.roles.developer import AICODeveloper
from metagpt.ext.aico.roles.qa_engineer import AICOQaEngineer
from metagpt.team import Team

app = typer.Typer(add_completion=False)

@app.command()
def run_aico(
    idea: str = typer.Argument(..., help="项目需求描述"),
    investment: float = typer.Option(default=10.0, help="投资金额"),
    n_round: int = typer.Option(default=5, help="最大对话轮数"),
    output_root: str = typer.Option(default="output", help="输出目录"),
):
    """运行AICO项目"""
    
    # 初始化环境
    env = AICOEnvironment()
    
    # 创建团队
    team = Team(env=env)
    
    # 雇佣角色
    team.hire([
        AICOProjectManager(output_root_dir=Path(output_root)),
        AICOBusinessAnalyst(output_root_dir=Path(output_root)),
        # AICOProductManager(output_root_dir=Path(output_root)),
        # AICOEnterpriseArchitect(output_root_dir=Path(output_root)),
        # AICODeveloper(output_root_dir=Path(output_root)),
        # AICOQaEngineer(output_root_dir=Path(output_root))
    ])
    
    # 投资
    team.invest(investment)
    
    # 启动项目
    team.run_project(idea=idea)
    
    # 运行
    asyncio.run(team.run(n_round=n_round))

if __name__ == "__main__":
    app()
