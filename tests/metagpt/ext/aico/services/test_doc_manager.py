# 测试 @metagpt/ext/aico/services/doc_manager.py
## doc_manager代码目标覆盖率：80%以上
## 测试的目录和数据放在 @tests/data/aico/services/doc_manager


# 运行测试
# pytest tests/metagpt/ext/aico/services/test_doc_manager.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/*.py"

import pytest
from pathlib import Path
from metagpt.ext.aico.services.doc_manager import AICODocManager, AICORepo, AICODocument, DocType
from metagpt.config2 import  config


from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM


@pytest.fixture
def tmp_project(tmp_path):
    """按规范初始化目录结构"""
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "VERSION").write_text("1.0.0")
    (tmp_path / "tracking").mkdir()
    
    # 需求相关目录
    (tmp_path / "docs/requirements/raw").mkdir(parents=True)
    analyzed_dir = tmp_path / "docs/requirements/analyzed/1.0.0"
    analyzed_dir.mkdir(parents=True)
    
    # 设计相关目录
    (tmp_path / "docs/design/services/auth/1.0.0").mkdir(parents=True)
    (tmp_path / "docs/design/tests/auth/1.0.0").mkdir(parents=True)
    
    # 发布目录
    (tmp_path / "releases/1.0.0").mkdir(parents=True)
    
    return tmp_path


@pytest.fixture
def mock_llm():
    return MockLLM()

@pytest.fixture
def mock_embedding():
    return MockEmbedding(embed_dim=1536)


@pytest.fixture
def doc_manager(tmp_project, mock_embedding, mock_llm):
    """创建文档管理器实例"""
    repo = AICORepo(tmp_project)
    manager = AICODocManager(repo, mock_embedding, mock_llm)
    
    return manager

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """模拟运行环境"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config.embedding, 'api_type', 'mock')
    config.omniparse.base_url = "http://mock-omniparse"
    config.omniparse.api_key = "test-key"

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

        # 创建文档时不再传递version参数
        doc = await doc_manager.create_document(
            DocType.USER_STORY,
            req_id="US001",
            scenario="用户登录场景",
            acceptance_criteria=["成功跳转主页", "错误提示明确"]
        )
        
        # 验证文件存在
        full_path = tmp_project / doc.path
        assert full_path.exists()
        assert "用户登录场景" in full_path.read_text()
        
        # 验证用户故事路径
        assert "docs/requirements/analyzed/1.0.0/user_stories.md" in str(doc.path)
        
        # 读取文档
        read_doc = await doc_manager.get_document(
            DocType.USER_STORY,
            req_id="US001",
        )
        assert read_doc is not None
        assert read_doc.content == doc.content
        
        # 搜索文档
        results = await doc_manager.search_documents("用户登录场景", limit=5)
        assert len(results) > 0
        assert "用户登录" in results[0]['content']
    
    
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
        
        # 验证技术架构路径
        assert "docs/ea/tech_arch/1.0.0/tech_arch.md" in str(tech_arch_doc.path)
        
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

@pytest.mark.asyncio
async def test_edge_cases():
    """边界条件测试套件"""
    # 测试空仓库初始化
    empty_repo = AICORepo(Path("/non_exist"))
    assert empty_repo.current_version == "0.0.0"
    
    # 测试无效文档获取
    manager = AICODocManager(empty_repo)
    doc = await manager.get_document(DocType.PRD)
    assert doc is None

class TestAICOTemplate:
    """测试模板生成功能"""
    
    def test_tech_arch_template(self):
        """场景：验证技术架构模板生成"""
        from metagpt.ext.aico.services.doc_manager import AICOTemplate
        
        content = AICOTemplate.generate(DocType.TECH_ARCH, {
            "version": "1.0.0",
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
            "version": "1.0.0",
            "apis": [
                {
                    "method": "POST",
                    "path": "/login",
                    "description": "用户登录接口",
                    "params": {"username": "字符串", "password": "字符串"},
                    "response": {"token": "JWT字符串"}
                }
            ]
        })
        
        # 验证关键内容
        assert "## 接口列表" in content
        assert "### POST /login" in content
        assert "功能: 用户登录接口" in content

def test_api_spec_path(tmp_project):
    """验证API规范路径生成"""
    repo = AICORepo(tmp_project)
    path = repo.get_doc_path(DocType.API_SPEC, service="auth")
    # 转换为相对路径后再断言
    rel_path = path.relative_to(tmp_project)
    assert str(rel_path) == "docs/api/1.0.0/spec.md"

def test_version_directory_creation(tmp_project):
    """验证版本更新时目录创建"""
    repo = AICORepo(tmp_project)
    repo.update_version("2.0.0")
    
    expected_dirs = [
        "docs/requirements/analyzed/2.0.0",
        "docs/ea/tech_arch/2.0.0",
        "docs/api/2.0.0",  # 修正预期路径
        "releases/2.0.0"
    ]
    for d in expected_dirs:
        assert (tmp_project / d).exists()


