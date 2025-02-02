#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14
@Author  : Jiacheng Cai
@File    : project_manager.py
说明:
  项目经理(PM)角色职责:
  1. 初始化项目,生成项目基本信息
  2. 跟踪原始需求素材的解析状态
  3. 复核业务需求和技术需求,形成需求基线
  4. 制定迭代计划,分配任务
  5. 复核设计文档,确保一致性
  6. 复核任务分解,确保可执行性
"""
from typing import Dict, List
from pathlib import Path
import json
from datetime import datetime
from openpyxl import load_workbook, Workbook
from metagpt.roles import Role
from metagpt.actions import ActionOutput
from metagpt.environment.aico.aico_env import AICOEnvironment
from ..actions.pm_action import (
    ReviewRequirement, ReviewDesign, ReviewAllRequirements
)
from metagpt.utils.common import format_message
import logging
from metagpt.ext.aico.config import config
import shutil
import asyncio
from ..services.project_tracking_service import ProjectTrackingService, TrackingSheet, ColumnIndex

logger = logging.getLogger(__name__)

class AICOProjectManager(Role):
    """AICO项目经理（遵循docs/aico/specs/目录下规范）"""
    
    name: str = "AICO_PM"
    profile: str = "Project Manager"
    goal: str = "根据AICO规范管理项目全生命周期"
    constraints: str = "严格遵循EA设计规范和项目管理规范"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewRequirement, ReviewDesign, ReviewAllRequirements])  # 只保留需要LLM交互的Action
        self._init_project()  # 项目初始化改为角色内部方法
        self.tracking_svc = ProjectTrackingService(
            self.project_root / "tracking/ProjectTracking.xlsx"
        )
        
    def _init_project(self):
        """初始化或加载项目结构"""
        if self.project_root.exists():
            logger.info(f"加载现有项目: {self.project_root}")
            # 调整顺序：先校验再同步
            tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
            if tracking_file.exists() and not self._validate_tracking_file():
                logger.error("项目跟踪表结构不兼容，请手动处理！")
                raise ValueError("ProjectTracking.xlsx schema mismatch")
            self._sync_specs()
            return
        
        # 创建新项目结构
        logger.info(f"初始化新项目: {self.project_root}")
        dirs = [
            "docs/aico/specs",  # 项目专属规范目录
            "docs/ea",
            "docs/requirements",
            "tracking",
            "src",
            "config"
        ]
        for d in dirs:
            (self.project_root / d).mkdir(parents=True, exist_ok=True)
        
        self._sync_specs(force=True)  # 强制同步规范模板
        self._create_tracking_file()
        
    def _sync_specs(self, force: bool = False):
        """同步规范文件（项目规范优先于全局规范）"""
        global_spec_root = Path(config.workspace.specs)  # 全局规范路径
        project_spec_dir = self.project_root / "docs/aico/specs"
        
        # 拷贝全局规范到项目目录（不覆盖已有文件）
        for spec_file in global_spec_root.glob("*.md"):
            target = project_spec_dir / spec_file.name
            if not target.exists() or force:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(spec_file, target)
                logger.debug(f"同步规范文件: {spec_file.name}")

    def get_spec(self, spec_type: str) -> str:
        """获取规范内容（项目规范优先）"""
        project_spec = self.project_root / "docs/aico/specs" / f"{spec_type}_spec.md"
        global_spec = Path(config.workspace.specs) / f"{spec_type}_spec.md"
        
        if project_spec.exists():
            return project_spec.read_text(encoding="utf-8")
        elif global_spec.exists():
            return global_spec.read_text(encoding="utf-8")
        raise FileNotFoundError(f"规范文件不存在: {spec_type}")

    def _create_tracking_file(self):
        """创建项目跟踪表（改为通过服务类）"""
        self.tracking_svc = ProjectTrackingService(
            self.project_root / "tracking/ProjectTracking.xlsx"
        )
        self.tracking_svc.save()

    async def _act(self) -> None:
        """遵循README_AICO_CN_1.2.md的时序逻辑"""
        # 阶段1：需求收集
        await self._process_requirements()
        
        # 阶段2：需求设计
        await self._process_design()
        
        # 阶段3：实现跟踪
        await self._process_implementation()

    async def _process_requirements(self):
        """处理需求全流程（从config获取）"""
        # 从config获取原始需求
        raw_req = config.extra.get("raw_requirement")
        if not raw_req:
            logger.warning("未找到原始需求配置")
            return
        
        # 保存需求文件
        req_file = self._save_requirement_file(raw_req)
        
        # 登记到跟踪表
        self._add_raw_requirement_to_tracking({
            "file_path": str(req_file.relative_to(self.project_root)),
            "type": raw_req["type"],
            "status": "待分析",
            "comment": raw_req.get("comment", "")
        })
        
        # 处理历史未分析需求（含重试机制）
        pending_reqs = self._get_pending_requirements()
        for req in pending_reqs:
            await self._dispatch_requirement_analysis(req)
        pass

    async def _handle_new_requirement(self, msg):
        """处理新输入的原始需求"""
        # 保存到项目目录（根据文档5.2节）
        req_file = self._save_requirement_file(msg.content)
        
        # 登记到跟踪表（文档6.1.1节）
        self._add_raw_requirement_to_tracking({
            "file_path": str(req_file.relative_to(self.project_root)),
            "type": msg.content.get("type", "business"),
            "status": "待分析",
            "comment": msg.content.get("comment", "")
        })
        
        logger.info(f"新增需求登记完成：{req_file.name}")

    def _save_requirement_file(self, req_data: dict) -> Path:
        """保存需求文件到统一目录"""
        reqs_dir = self.project_root / "docs/requirements/raw"
        reqs_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（时间戳+类型）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"REQ_{timestamp}_{req_data['type']}.txt"
        req_file = reqs_dir / filename
        
        # 写入纯文本内容
        req_file.write_text(req_data["content"], encoding="utf-8")
        return req_file

    def _add_raw_requirement_to_tracking(self, req_info: dict):
        """添加需求到跟踪表"""
        tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
        try:
            wb = load_workbook(tracking_file)
            ws = wb["原始需求"]
            
            new_row = [
                req_info["file_path"],    # 需求文件
                req_info["type"],         # 需求类型
                datetime.now().isoformat(), # 添加时间
                req_info["status"],       # 当前状态
                "",                       # 关联需求ID（初始为空）
                "",                       # BA解析时间
                "",                       # EA解析时间
                "",                       # 完成时间
                req_info["comment"]       # 备注
            ]
            ws.append(new_row)
            wb.save(tracking_file)
        except Exception as e:
            logger.error(f"跟踪表更新失败：{str(e)}")
            raise RuntimeError("需求登记失败") from e

    def _get_pending_requirements(self) -> list:
        """获取待处理的需求列表"""
        tracking_file = self.project_root / "tracking/ProjectTracking.xlsx"
        pending = []
        
        try:
            wb = load_workbook(tracking_file)
            ws = wb["原始需求"]
            
            for row in ws.iter_rows(min_row=2):
                # 检查状态列（第4列）和解析时间列（5-6列）
                status = row[3].value
                ba_time = row[5].value
                ea_time = row[6].value
                
                if status == "待分析" or not ba_time or not ea_time:
                    pending.append({
                        "file": row[0].value,
                        "type": row[1].value,
                        "added_time": row[2].value,
                        "status": status
                    })
        except Exception as e:
            logger.error(f"读取跟踪表失败：{str(e)}")
        
        return pending

    async def _dispatch_requirement_analysis(self, req_info: dict):
        """使用跟踪服务处理需求分析"""
        req_file = self.project_root / req_info["file"]
        raw_req_path = str(req_file.relative_to(self.project_root))
        
        # 检查BA分析状态
        if not self.tracking_svc.get_raw_requirement_status(raw_req_path) or \
           not self.tracking_svc.get_raw_requirement_status(raw_req_path).get("ba_time"):
            await self._process_ba_analysis(req_file, raw_req_path)
            
        # 检查EA分析状态    
        if not self.tracking_svc.get_raw_requirement_status(raw_req_path) or \
           not self.tracking_svc.get_raw_requirement_status(raw_req_path).get("ea_time"):
            await self._process_ea_analysis(req_file, raw_req_path)

    async def _process_ba_analysis(self, req_file: Path, raw_req_path: str):
        """处理BA分析流程"""
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_BIZ_ANALYSIS, {
            "req_id": req_file.stem,
            "file_path": str(req_file),
            "type": "business"
        })
        
        async for ba_msg in self.observe(AICOEnvironment.MSG_BA_ANALYSIS_DONE):
            if ba_msg.content["req_id"] == req_file.stem:
                # 生成业务需求ID
                biz_req_id = f"RQ-B-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # 使用服务类更新跟踪表
                self.tracking_svc.add_requirement(
                    req_id=biz_req_id,
                    raw_file=raw_req_path,
                    req_data=ba_msg.content["standard_req"],
                    output_files=ba_msg.content["output_files"]
                )
                
                self.tracking_svc.add_user_stories(
                    biz_req_id=biz_req_id,
                    stories=ba_msg.content["user_stories"]
                )
                
                self.tracking_svc.update_raw_requirement_status(
                    file_path=raw_req_path,
                    status="业务分析完成"
                )
                self.tracking_svc.save()
                break

    async def _process_ea_analysis(self, req_file: Path, raw_req_path: str):
        """处理EA分析流程"""
        await self.publish(AICOEnvironment.MSG_REQUIREMENT_TECH_ANALYSIS, {
            "req_id": raw_req_path.split("/")[-1],
            "biz_req_id": raw_req_path.split("/")[-1].split("-")[1],
            "file_path": raw_req_path
        })
        
        async for ea_msg in self.observe(AICOEnvironment.MSG_EA_ANALYSIS_DONE):
            # 生成技术需求ID
            tech_req_id = f"RQ-T-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 更新跟踪表
            self.tracking_svc.add_requirement(
                req_id=tech_req_id,
                raw_file=raw_req_path,
                req_data=ea_msg.content["tech_req"],
                output_files=ea_msg.content["output_files"]
            )
            
            self.tracking_svc.update_raw_requirement_status(
                file_path=raw_req_path,
                status="技术分析完成"
            )

    async def _process_design(self):
        """处理设计阶段"""
        design_msg = await self.observe("design_doc")
        if design_msg:
            review_result = await self.rc.run(
                ReviewDesign().run(design_msg.content)
            )
            
            # 发布设计基线（根据文档6.2节）
            await self.publish("design:baseline", {
                "prd": design_msg.content,
                "review": review_result.instruct_content
            })

    async def _process_implementation(self):
        """处理实现跟踪（根据文档6.3节）"""
        # 监听任务相关消息并更新跟踪表
        async for msg in self.observe("task_update"):
            self._update_task_status(msg.content)
            
    def _update_tracking(self, data: dict):
        """更新跟踪表（TODO: 需要实现Excel操作）"""
        logger.debug(f"更新需求跟踪表：{format_message(data)}")
        
    def _update_task_status(self, task_info: dict):
        """更新任务状态（TODO: 需要实现Excel操作）"""
        logger.debug(f"更新任务状态：{format_message(task_info)}")
        
    def _update_raw_req_status(self, tracking_file: Path, req_file: Path, 
                              status: str = "new", role: str = None,
                              req_id: str = None):
        """更新Excel中的原始需求状态
        
        Args:
            tracking_file: ReqTracking.xlsx 路径
            req_file: 需求文件路径
            status: 状态(new/parsed_by_ba/parsed_by_ea/completed)
            role: 角色(BA/EA)
            req_id: 关联需求ID
        """
        wb = load_workbook(tracking_file)
        ws = wb["原始需求"]
        
        # 查找现有行
        req_key = str(req_file)
        existing_row = None
        for row in ws.iter_rows(min_row=2):
            if row[0].value == req_key:
                existing_row = row
                break
                
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing_row:
            # 修复：增加状态变更校验
            if status == "parsed_by_ba" and existing_row[3].value == "parsed_by_ea":
                new_status = "completed"
            elif status == "parsed_by_ea" and existing_row[3].value == "parsed_by_ba":
                new_status = "completed"
            else:
                new_status = status
            
            existing_row[3].value = new_status  # 替换原来的直接赋值
            if req_id:
                existing_row[4].value = req_id
            if role == "BA":
                existing_row[5].value = current_time  # 更新BA解析时间
            elif role == "EA":
                existing_row[6].value = current_time  # 更新EA解析时间
            if status == "completed":
                existing_row[7].value = current_time  # 更新完成时间
        else:
            # 添加新行
            new_row = [
                req_key,  # 需求文件
                "文档" if req_key.endswith((".md", ".txt", ".docx")) else "其他",  # 需求类型
                current_time,  # 添加时间
                status,  # 当前状态
                req_id,
                current_time if role == "BA" else None,  # BA解析时间
                current_time if role == "EA" else None,  # EA解析时间
                current_time if status == "completed" else None,  # 完成时间
                ""  # 备注
            ]
            ws.append(new_row)
            
        wb.save(tracking_file)
        
    def _validate_tracking_file(self) -> bool:
        """校验跟踪表结构（改为通过服务类）"""
        try:
            # 服务类内部实现校验逻辑
            self.tracking_svc._get_workbook()
            return True
        except Exception as e:
            logger.error(f"跟踪文件校验失败: {str(e)}")
            return False

    def get_requirement_status(self, req_id: str) -> dict:
        """获取需求状态"""
        return self.tracking_svc.get_requirement_status(req_id)

    def update_task_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        self.tracking_svc.update_task_progress(task_id, progress)
        self.tracking_svc.save()

# 打印当前工作空间配置
print(config.workspace)
