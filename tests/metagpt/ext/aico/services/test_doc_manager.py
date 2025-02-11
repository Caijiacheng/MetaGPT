# 测试 @metagpt/ext/aico/services/doc_manager.py
## 测试的目录和数据放在 @tests/data/aico/services/doc_manager
## 测试要求：
### 模拟外部调用的场景，测试完整的版本管理流程workflow，可以调用到所有的函数 
### 针对每个函数，提供单元测试，确保函数功能正确，并且有异常测试的场景，覆盖到80%以上的代码

# 运行测试
# pytest tests/metagpt/ext/aico/services/test_doc_manager.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/doc_manager.py"

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
    manager = AICODocManager(
        repo=repo,
        embed_model=mock_embedding,
        llm=mock_llm
    )
    
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
    

    def test_invalid_service_name(self, tmp_project):
        """测试无效服务名称的路径生成"""
        repo = AICORepo(tmp_project)
        
        with pytest.raises(ValueError):
            repo.get_doc_path(DocType.API_DESIGN, service="invalid/service/name")

    def test_invalid_component_name(self, tmp_project):
        """测试无效组件名称处理"""
        repo = AICORepo(tmp_project)
        
        with pytest.raises(ValueError):
            AICODocument.create(
                repo=repo,
                doc_type=DocType.TECH_ARCH,
                content="架构内容",
                components=[{"name": "invalid*component", "description": "无效组件"}]
            )

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
        assert "docs/ea/1.0.0/tech_arch.md" in str(doc.path)
        
        # 新增文件存在性检查
        assert doc.path.exists()
        assert "架构内容" in doc.path.read_text()

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
        assert "docs/ea/1.0.0/user_stories.md" in str(doc.path)
        
        # 读取文档
        read_doc = await doc_manager.get_document(
            DocType.USER_STORY,
            context={"req_id": "US001"}
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
        assert "docs/ea/1.0.0/tech_arch.md" in str(tech_arch_doc.path)
        
        # 测试测试用例模板
        test_case_doc = await doc_manager.create_document(
            DocType.TEST_CASE_DESIGN,
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
    async def test_create_document_with_missing_args(self, doc_manager):
        """测试创建文档时缺少必要参数"""
        with pytest.raises(ValueError):
            # 缺少req_id参数
            await doc_manager.create_document(
                DocType.USER_STORY,
                scenario="测试场景"
            )

    @pytest.mark.asyncio
    async def test_template_generation_failure(self, doc_manager):
        """测试模板生成失败场景"""
        with pytest.raises(ValueError):
            # 缺少必要参数components
            await doc_manager.create_document(
                DocType.TECH_ARCH,
                diagram_url="arch.png"
            )

@pytest.mark.asyncio
async def test_edge_cases(tmp_project, monkeypatch):
    """边界条件测试套件"""
    # 测试空仓库初始化应抛出异常
    with pytest.raises(ValueError):
        AICORepo(Path("/non_exist"))
    
    # 测试无效文档获取
    valid_repo = AICORepo(tmp_project)
    manager = AICODocManager(valid_repo)
    doc = await manager.get_document(DocType.PRD)
    assert doc is None

    # 新增文件权限测试
    # valid_path = tmp_project / "docs/specs/perm_test.md"
    # valid_path.touch()
    
    # 模拟无写权限
    # def mock_write(*args, **kwargs):
    #     raise PermissionError("No write permission")
        
    # monkeypatch.setattr(valid_path, 'write_text', mock_write)
    # with pytest.raises(PermissionError):
    #     valid_path.write_text("test")

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
        
        content = AICOTemplate.generate(DocType.API_DESIGN, {
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

    def test_invalid_template_parameters(self):
        """测试模板参数验证"""
        from metagpt.ext.aico.services.doc_manager import AICOTemplate
        
        with pytest.raises(ValueError):
            # 缺少必要字段version
            AICOTemplate.generate(DocType.TECH_ARCH, {
                "components": [],
                "diagram_url": "arch.png"
            })

def test_api_spec_path(tmp_project):
    """验证API规范路径生成"""
    repo = AICORepo(tmp_project)
    path = repo.get_doc_path(DocType.API_DESIGN, service="auth")
    # 转换为相对路径后再断言
    rel_path = path.relative_to(tmp_project)
    assert str(rel_path) == "docs/design/services/auth/1.0.0/api_design.md"

def test_version_directory_creation(tmp_project):
    """验证版本更新时目录创建"""
    repo = AICORepo(tmp_project)
    repo.update_version("2.0.0")
    
    # 创建文档时使用正确的参数名req_id
    doc = AICODocument.create(
        repo=repo,
        doc_type=DocType.BIZ_REQUIREMENT,
        req_id="REQ001",
        content="业务需求分析",
        version="2.0.0"
    )

    expected_dirs = [
        "docs/requirements/analyzed/2.0.0/REQ001",  # 需求分析目录
    ]
    for d in expected_dirs:
        assert (tmp_project / d).exists(), f"目录不存在: {d}"
    


    # 验证文件路径
    expected_file = tmp_project / "docs/requirements/analyzed/2.0.0/REQ001/biz_analysis.md"
    assert expected_file.exists(), "需求分析文件未生成"
    
    # 验证版本文件
    version_file = tmp_project / "VERSION"
    assert version_file.read_text() == "2.0.0"

@pytest.mark.asyncio
async def test_invalid_doc_creation(doc_manager):
    """测试创建无效类型文档"""
    with pytest.raises(ValueError):
        await doc_manager.create_document("INVALID_TYPE")

def test_invalid_version_update(tmp_project):
    """测试非法版本号更新"""
    repo = AICORepo(tmp_project)
    with pytest.raises(ValueError):
        repo.update_version("invalid_version")

@pytest.mark.asyncio 
async def test_nonexistent_doc_retrieval(doc_manager):
    """测试获取不存在的文档"""
    doc = await doc_manager.get_document(
        DocType.PRD,
        context={"identifier": "NON_EXIST"}
    )
    assert doc is None

# 补充测试新的文档类型
def test_service_design_document(tmp_project):
    repo = AICORepo(tmp_project)
    path = repo.get_doc_path(DocType.SERVICE_DESIGN, service="payment", version="1.0.0")
    assert str(path.relative_to(tmp_project)) == "docs/design/services/payment/1.0.0/service_design.md"

# 测试新增的组件名称校验
def test_component_name_validation(tmp_project):
    repo = AICORepo(tmp_project)
    with pytest.raises(ValueError):
        AICODocument.create(
            repo=repo,
            doc_type=DocType.TECH_ARCH,
            content="test",
            components=[{"name": "invalid*comp", "description": ""}]
        )


