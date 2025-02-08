# 测试PM的角色以及P0阶段的工作流程
## 代码覆盖率80%以上
## LLM 的输出采用mock输出
## 测试的目录和数据放在 @tests/data/aico/p0
## 测试的流程采用pytest的测试流程
## 测试的过程，需要验证整个projectTracking.xlsx的完整性
## 测试的过程，需要验证整个项目目录的完整性
## 测试的过程，需要验证整个项目文档的完整性（BA/EA在P0阶段的工作文档采用mock输出）
## 测试的过程，与BA/EA协同工作，采用mock输出
## 测试用例，要能覆盖所有的PM角色中的函数定义，并且说明测试的场景

## 项目的原始需求是：搭建一个商品品牌管理档案，包含品牌信息管理、品牌信息查询、品牌信息分析
## 项目的原始需求文件是：docs/requirements/raw/iter1_brand.md

import pytest
from unittest.mock import AsyncMock
from metagpt.ext.aico.actions.pm_action import ReviewAllRequirements
from metagpt.ext.aico.roles.project_manager import AICOProjectManager
from metagpt.ext.aico.services import DocType
from metagpt.ext.aico.services.project_tracking_manager import ProjectTrackingManager

async def test_project_initialization(project_dir):
    """测试项目初始化流程（文档5.2节）"""
    pm = AICOProjectManager(project_root=project_dir)
    doc_manager = pm.doc_manager  # 获取文档管理服务
    
    pm._init_project()

    # 验证基础目录结构（通过DocType获取路径）
    raw_req_path = doc_manager.get_doc_path(DocType.REQUIREMENT_RAW, create_dir=False)
    tracking_path = doc_manager.get_doc_path(DocType.PROJECT_TRACKING, create_dir=False)
    
    assert raw_req_path.exists()
    assert tracking_path.exists()
    
    # 验证跟踪文件初始化
    tracking_file = doc_manager.get_doc_path(DocType.PROJECT_TRACKING)
    assert tracking_file.exists()
    
    # 验证版本文件
    version_file = doc_manager.get_doc_path(DocType.VERSION)
    assert version_file.read_text().strip() == "0.1.0"

async def test_requirement_lifecycle(project_dir, mocker):
    """测试端到端需求生命周期（文档6.1节全流程）"""
    pm = AICOProjectManager(project_root=project_dir)
    doc_manager = pm.doc_manager
    pm._init_project()
    
    # 1. 添加原始需求（使用标准文档类型）
    req_file = doc_manager.get_doc_path(DocType.REQUIREMENT_RAW) / "raw_req.md"
    req_file.write_text("# 商品品牌管理需求")
    
    await pm._process_input_requirement({
        "file_path": str(req_file),
        "type": "business",
        "description": "品牌基础功能",
        "source": "用户"
    })
    
    # 2. 模拟BA分析（使用版本服务生成路径）
    version = pm.version_svc.bump("minor")
    output_path = doc_manager.get_doc_path(
        DocType.REQUIREMENT_ANALYZED,
        version=version,
        req_id="REQ-001"
    ) / "biz_analysis.md"
    
    mock_observe = mocker.patch.object(pm, 'observe', AsyncMock(return_value=AsyncMock(
        content={
            "req_id": "REQ-001",
            "standard_req": "实现品牌CRUD功能",
            "user_stories": [{"story_id": "US-001", "title": "品牌创建"}],
            "output_files": [str(output_path)]  # 使用标准路径格式
        }
    )))
    
    await pm._parse_raw_requirements()
    
    # 验证需求状态更新
    tracking = ProjectTrackingManager(doc_manager.get_doc_path(DocType.PROJECT_TRACKING))
    req_status = tracking.get_requirement_status("REQ-001")
    assert req_status["status"] == "parsed_by_ba"
    
    # 3. 模拟架构分析
    await pm._process_arch_analysis()
    
    # 4. 需求基线确认
    review_result = await pm.rc.run(ReviewAllRequirements().run({
        "version": "0.2.0",
        "requirements": {
            "business_requirements": [{"id": "REQ-001"}],
            "technical_requirements": []
        }
    }))
    assert "ai_approved_reqs" in review_result.content

async def test_requirement_review_action(project_dir):
    """测试需求评审动作（pm_action.ReviewAllRequirements）"""
    action = ReviewAllRequirements()
    
    # 模拟上下文数据
    context = {
        "version": "1.0.0",
        "requirements": {
            "business_requirements": [
                {"id": "REQ-001", "description": "品牌管理"}
            ],
            "technical_requirements": [
                {"id": "TECH-001", "biz_id": "REQ-001", "description": "品牌API"}
            ],
            "user_stories": [
                {"req_id": "REQ-001", "status": "TODO"}
            ]
        }
    }
    
    result = await action.run(context)
    
    # 验证输出结构
    assert not result.content["ai_approved_reqs"]
    assert "human_confirmed" in result.content

async def test_design_review_process(project_dir, mocker):
    """测试设计文档复核流程（文档6.2节）"""
    pm = AICOProjectManager(project_root=project_dir)
    doc_manager = pm.doc_manager
    pm._init_project()
    
    # 生成符合规范的设计文档路径
    design_path = doc_manager.get_doc_path(
        DocType.SERVICE_DESIGN,
        version="0.1.0",
        service="brand"
    )
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text("服务设计文档内容")
    
    # 模拟设计文档提交
    mocker.patch.object(pm, 'observe', AsyncMock(return_value=AsyncMock(
        content=str(design_path)  # 传递标准路径
    )))
    
    # 执行设计复核
    await pm._process_design()
    
    # 验证跟踪表更新
    tracking = ProjectTrackingManager(doc_manager.get_doc_path(DocType.PROJECT_TRACKING))
    designs = tracking.get_baseline_requirements("design")
    assert len(designs) > 0

async def test_version_management(project_dir):
    """测试版本管理功能（文档版本规范）"""
    pm = AICOProjectManager(project_root=project_dir)
    doc_manager = pm.doc_manager
    pm._init_project()
    
    # 初始版本
    assert pm.version_svc.current == "0.1.0"
    
    # 次版本升级
    new_version = pm.version_svc.bump("minor")
    assert new_version == "0.2.0"
    
    # 验证版本目录创建（通过DocType获取路径）
    analyzed_path = doc_manager.get_doc_path(
        DocType.REQUIREMENT_ANALYZED,
        version=new_version,
        create_dir=False
    )
    assert analyzed_path.exists()

async def test_invalid_requirement_handling(project_dir):
    """测试异常需求处理（文档5.2节边界条件）"""
    pm = AICOProjectManager(project_root=project_dir)
    pm._init_project()
    
    # 无效需求输入
    with pytest.raises(ValueError):
        await pm._process_input_requirement({"invalid": "data"})
        
    # 重复需求文件
    req_file = project_dir / "dup_req.md"
    req_file.write_text("# 重复需求")
    await pm._process_input_requirement({"file_path": str(req_file), "type": "business"})
    with pytest.raises(ValueError):
        await pm._process_input_requirement({"file_path": str(req_file), "type": "business"})










