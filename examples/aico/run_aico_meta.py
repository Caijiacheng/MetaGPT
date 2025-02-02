#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/15
@Author  : Jiacheng Cai
@File    : run_aico_meta.py
说明:
  AICO项目启动入口（重构版）:
  1. 统一配置管理
  2. 优化参数处理逻辑
  3. 增强环境配置能力
"""
import asyncio
from pathlib import Path
import typer
from typing import Optional

from metagpt.config2 import config
from metagpt.environment.aico.aico_env import AICOEnvironment
from metagpt.ext.aico.roles import (
    AICOProjectManager,
    AICOBusinessAnalyst,
    AICOEnterpriseArchitect
)
from metagpt.team import Team

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

def load_requirement(req_input: str) -> str:
    """统一需求加载方法"""
    req_path = Path(req_input)
    if req_path.exists():
        return req_path.read_text(encoding="utf-8")
    return req_input  # 直接返回文本内容

@app.command()
def main(
    requirement: str = typer.Argument(..., help="需求输入（文本内容）"),
    project_name: str = typer.Option(None, help="项目名称（覆盖配置）"),
    output_root: str = typer.Option(None, help="输出目录（覆盖配置）"),
    n_round: int = typer.Option(5, help="最大对话轮数"),
    investment: float = typer.Option(10.0, help="投资金额"),
):
    """启动AICO项目"""
    # 处理需求输入（仅文本）
    config.extra.update({
        "raw_requirement": {
            "type": "business",  # 默认类型
            "content": requirement,
            "source": "cli_input"
        },
        "project_name": project_name or config.project_name,
        "output_root": output_root or str(config.workspace.project_root)
    })
    
    # 初始化环境
    env = AICOEnvironment(
        project_root=Path(config.workspace.project_root),
        specs_dir=Path(config.workspace.specs),
        tracking_dir=Path(config.workspace.tracking)
    )
    
    # 创建团队
    team = Team(env=env)
    
    # 初始化角色（带配置）
    roles = [
        AICOProjectManager(),
        AICOBusinessAnalyst(),
        AICOEnterpriseArchitect()
    ]
    
    # 运行项目
    team.hire(roles)
    team.invest(investment)
    team.run_project(idea=config.extra["requirement"])
    
    # 异步运行
    try:
        asyncio.run(team.run(n_round=n_round))
    except RuntimeError as e:
        logger.critical(f"需求处理失败: {str(e)}")
        exit(1)

def _process_requirement_input(req_input: str) -> dict:
    """统一处理需求输入"""
    req_path = Path(req_input)
    if req_path.exists():
        content = req_path.read_text(encoding="utf-8")
        return {
            "type": _detect_requirement_type(req_path),
            "content": content,
            "file_path": str(req_path)
        }
    else:
        return {
            "type": "business",
            "content": req_input,
            "source": "direct_input"
        }

def _detect_requirement_type(file_path: Path) -> str:
    """根据文件扩展名判断需求类型"""
    ext = file_path.suffix.lower()
    return {
        ".md": "business",
        ".xlsx": "structured",
        ".txt": "interview",
        ".mp4": "media",
        ".mp3": "media"
    }.get(ext, "unknown")

if __name__ == "__main__":
    app()
