# 测试 @metagpt/ext/aico/services/doc_manager.py
## doc_manager代码目标覆盖率：80%以上
## 测试的目录和数据放在 @tests/data/aico/services/doc_manager


# 运行测试
# pytest tests/metagpt/ext/aico/services/test_doc_manager.py -v --cov=metagpt --cov-report=term

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from metagpt.ext.aico.services.doc_manager import (
    AICODocManager,
    AICORepo,
    AICODocument,
    DocType
)
from metagpt.provider.base_llm import BaseLLM

@pytest.fixture
def tmp_project(tmp_path):
    """初始化临时项目结构"""
    (tmp_path / "VERSION").write_text("1.0.0")
    (tmp_path / "tracking").mkdir()
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/requirements/raw").mkdir(parents=True)
    return tmp_path

@pytest.fixture
def mock_llm():
    """模拟LLM响应"""
    llm = MagicMock(spec=BaseLLM)
    llm.aask = AsyncMock(return_value="摘要内容")
    return llm

@pytest.fixture
def doc_manager(tmp_project, mock_llm):
    """创建文档管理器实例"""
    repo = AICORepo(tmp_project)
    return AICODocManager(repo, mock_llm)

class TestAICORepo:
    """测试仓库管理功能"""
    
    def test_version_management(self, tmp_project):
        """场景：测试版本号读取和更新"""
        # 初始版本读取
        repo = AICORepo(tmp_project)
        assert repo.current_version == "1.0.0"
        
        # 版本更新
        repo.update_version("2.0.0")
        assert (tmp_project / "VERSION").read_text() == "2.0.0"
        assert repo.current_version == "2.0.0"
    
    def test_document_classification(self, tmp_project):
        """场景：验证文档自动分类逻辑"""
        repo = AICORepo(tmp_project)
        
        # 测试规范文档分类
        spec_path = tmp_project / "docs/specs/pm_guide.md"
        assert repo._classify_document(spec_path) == "specs"
        
        # 测试需求文档分类
        req_path = tmp_project / "docs/requirements/raw/req001.md"
        assert repo._classify_document(req_path) == "requirements"
        
        # 测试设计文档分类
        design_path = tmp_project / "docs/design/services/auth/v1/service_design.md"
        assert repo._classify_document(design_path) == "design"

class TestAICODocument:
    """测试文档模型相关功能"""
    
    def test_document_creation(self, tmp_project):
        """场景：测试通过模板创建文档"""
        repo = AICORepo(tmp_project)
        doc = AICODocument.create(
            repo=repo,
            doc_type=DocType.TECH_ARCH,
            content="架构内容",
            components=[]
        )
        assert doc.version == "1.0.0"
        assert doc.doc_type == DocType.TECH_ARCH
        assert "docs/ea/tech_arch/1.0.0/tech_arch.md" in str(doc.path)

class TestAICODocManager:
    """测试文档服务核心功能"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, doc_manager, tmp_project):
        """场景：测试文档全生命周期管理（创建->读取->搜索->历史）"""
        # 创建文档
        doc = await doc_manager.create_document(
            DocType.USER_STORY,
            req_id="US001",
            version="1.0.0",
            scenario="用户登录场景",
            acceptance_criteria=["成功跳转主页", "错误提示明确"]
        )
        
        # 验证文件存在
        full_path = tmp_project / doc.path
        assert full_path.exists()
        assert "用户登录场景" in full_path.read_text()
        
        # 读取文档
        read_doc = await doc_manager.get_document(
            DocType.USER_STORY,
            req_id="US001",
            version="1.0.0"
        )
        assert read_doc is not None
        assert read_doc.content == doc.content
        
        # 搜索文档
        results = await doc_manager.search_documents("登录流程", limit=1)
        assert len(results) > 0
        assert "用户登录" in results[0]['content']
        
        # 验证历史记录
        history = await doc_manager.get_version_history(DocType.USER_STORY)
        assert any(d.version == "1.0.0" for d in history)
    
    @pytest.mark.asyncio
    async def test_template_generation(self, doc_manager):
        """场景：验证不同文档类型的模板生成"""
        # 测试技术架构模板
        tech_arch_doc = await doc_manager.create_document(
            DocType.TECH_ARCH,
            components=[{"name": "Auth", "description": "认证服务"}],
            diagram_url="arch.png"
        )
        assert "认证服务" in tech_arch_doc.content
        assert "![架构图](arch.png)" in tech_arch_doc.content
        
        # 测试测试用例模板
        test_case_doc = await doc_manager.create_document(
            DocType.TEST_CASE,
            service="auth",
            cases=[{
                "title": "登录测试",
                "preconditions": "已注册用户",
                "steps": [
                    {"num": 1, "action": "输入正确密码", "expected": "登录成功"}
                ]
            }]
        )
        assert "登录测试" in test_case_doc.content
        assert "输入正确密码 -> 预期结果: 登录成功" in test_case_doc.content
    
    @pytest.mark.asyncio
    async def test_spec_management(self, doc_manager, tmp_project):
        """场景：测试规范文件的获取逻辑"""
        # 创建项目规范
        spec_path = tmp_project / "docs/specs/dev_guide.md"
        spec_path.write_text("# 项目开发规范")
        
        # 获取规范
        content = doc_manager.get_specification(DocType.SPEC_DEV)
        assert "项目开发规范" in content
        
        # 测试全局规范回退
        spec_path.unlink()
        global_spec = Path(config.workspace.specs) / "spec_dev_spec.md"
        global_spec.parent.mkdir(exist_ok=True)
        global_spec.write_text("# 全局开发规范")
        content = doc_manager.get_specification(DocType.SPEC_DEV)
        assert "全局开发规范" in content

@pytest.mark.asyncio
async def test_edge_cases():
    """边界条件测试套件"""
    # 测试空仓库初始化
    empty_repo = AICORepo(Path("/non_exist"))
    assert empty_repo.current_version == "0.0.0"
    
    # 测试无效文档获取
    manager = AICODocManager(empty_repo)
    doc = await manager.get_document(DocType.PRD, version="1.0.0")
    assert doc is None

class TestAICOTemplate:
    """测试模板生成功能"""
    
    def test_tech_arch_template(self):
        """场景：验证技术架构模板生成"""
        from metagpt.ext.aico.services.doc_manager import AICOTemplate
        
        content = AICOTemplate.generate(DocType.TECH_ARCH, {
            "version": "1.0",
            "components": [
                {"name": "Auth", "description": "认证服务"},
                {"name": "Order", "description": "订单服务"}
            ],
            "diagram_url": "arch.png"
        })
        assert "## 架构组件" in content
        assert "- Auth: 认证服务" in content
        assert "![架构图](arch.png)" in content
    
    def test_api_spec_template(self):
        """场景：验证接口规范模板生成"""
        from metagpt.ext.aico.services.doc_manager import AICOTemplate
        
        content = AICOTemplate.generate(DocType.API_SPEC, {
            "service": "auth",
            "apis": [
                {"method": "POST", "path": "/login", "description": "用户登录接口"}
            ]
        })
        assert "POST /login: 用户登录接口" in content
