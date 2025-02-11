from pathlib import Path
from datetime import datetime
import shutil
from typing import ClassVar, Dict, List, Optional, Union, Protocol
from enum import Enum
from pydantic import Field, BaseModel
import os
import re

from metagpt.document import Document, Repo
from metagpt.utils.embedding import get_embedding

from metagpt.utils.redis import Redis
from metagpt.config2 import config

from metagpt.rag.engines.simple import SimpleEngine
from metagpt.rag.schema import FAISSRetrieverConfig


class DocType(str, Enum):
    """
    AICO文档类型枚举
    职责：定义系统支持的文档类型及其元数据，作为文档分类的唯一标识
    包含：项目管理、需求分析、技术设计等全生命周期文档类型
    """
    PROJECT_TRACKING = "project_tracking"
    VERSION_PLAN = "version_plan"
    SPEC_PM = "spec_pm"
    SPEC_BA = "spec_ba"
    SPEC_EA = "spec_ea"
    SPEC_PRD = "spec_prd"
    SPEC_DEV = "spec_dev"
    SPEC_QA = "spec_qa"
    SPEC_API = "spec_api"
    REQUIREMENT_RAW = "requirement_raw"
    TECH_REQUIREMENT = "tech_requirement"
    BIZ_REQUIREMENT = "biz_requirement"
    BUSINESS_ARCH = "business_arch"
    USER_STORY = "user_story"
    TECH_ARCH = "tech_arch"
    PRD = "prd"
    SERVICE_DESIGN = "service_design"
    API_DESIGN = "api_design"   
    TEST_CASE_DESIGN = "test_case_design"
    RELEASE_NOTE = "release_note"
    


class AICORepo(Repo):
    """
    AICO规范仓库实现
    职责：
    - 管理符合AICO规范的代码仓库目录结构
    - 版本号管理（读取/更新VERSION文件）
    - 生成符合规范的文档存储路径
    - 维护文档分类逻辑
    - 确保物理目录结构完整性
    """
    
    _PATH_SPECS = "docs/specs"
    _PATH_REQUIREMENTS = "docs/requirements"
    _PATH_REQ_RAW = "docs/requirements/raw"
    _PATH_REQ_ANALYZED = "docs/requirements/analyzed"
    _PATH_EA_ARCH = "docs/ea"
    _PATH_DESIGN_PRD = "docs/design/prd"
    _PATH_DESIGN_SERVICES = "docs/design/services"
    _PATH_RELEASES = "releases"

    _PATH_SPECS_FILES = [
        _PATH_SPECS + "/pm_guide.md",
        _PATH_SPECS + "/ba_guide.md",
        _PATH_SPECS + "/ea_guide.md",
        _PATH_SPECS + "/prd_guide.md",
        _PATH_SPECS + "/dev_guide.md",
        _PATH_SPECS + "/qa_guide.md",
        _PATH_SPECS + "/api_guide.md",
    ]


    _PATH_TEMPLATES = {
        DocType.PROJECT_TRACKING: "project_tracking.xlsx",
        DocType.VERSION_PLAN: "VERSION",
        DocType.SPEC_PM: _PATH_SPECS + "/pm_guide.md",
        DocType.SPEC_BA: _PATH_SPECS + "/ba_guide.md",
        DocType.SPEC_EA: _PATH_SPECS + "/ea_guide.md",
        DocType.SPEC_PRD: _PATH_SPECS + "/prd_guide.md",
        DocType.SPEC_DEV: _PATH_SPECS + "/dev_guide.md",
        DocType.SPEC_QA: _PATH_SPECS + "/qa_guide.md",
        DocType.SPEC_API: _PATH_SPECS + "/api_guide.md",
        DocType.REQUIREMENT_RAW: _PATH_REQ_RAW + "/{version}/{req_id}.md",
        DocType.TECH_REQUIREMENT: _PATH_REQ_ANALYZED + "/{version}/{req_id}/tech_analysis.md",
        DocType.BIZ_REQUIREMENT: _PATH_REQ_ANALYZED + "/{version}/{req_id}/biz_analysis.md",
        DocType.BUSINESS_ARCH: _PATH_EA_ARCH + "/{version}/biz_arch.md",
        DocType.USER_STORY: _PATH_EA_ARCH + "/{version}/user_stories.md",
        DocType.TECH_ARCH: _PATH_EA_ARCH + "/{version}/tech_arch.md",
        DocType.PRD: _PATH_DESIGN_PRD + "/{version}/prd.md",
        DocType.SERVICE_DESIGN: _PATH_DESIGN_SERVICES + "/{service}/{version}/service_design.md",
        DocType.API_DESIGN: _PATH_DESIGN_SERVICES + "/{service}/{version}/api_design.md",
        DocType.TEST_CASE_DESIGN: _PATH_DESIGN_SERVICES + "/{service}/{version}/test_cases.md",
        DocType.RELEASE_NOTE: _PATH_RELEASES + "/{version}/release_note.md"
    }
    
    _INVAID_VERSION_: ClassVar[str] = "0.0.0"

    def __init__(self, path: Path):
        super().__init__(path=path)
        self._current_version = self._read_version()
        if self._current_version == self._INVAID_VERSION_:
            raise ValueError("项目未初始化")

    @classmethod
    def init_project(cls, path: Path, specs: List[Path], version: str = "1.0.0", **kwargs):
        """替代构造函数：从路径初始化"""
        if path.exists():
            raise FileExistsError(f"项目路径已存在: {path}")
        
        # 初始化所有目录文件
        for path in cls._PATH_DIRS:
            (path).mkdir(parents=True, exist_ok=True)
            pass

        # copy所有规范文件
        for spec in specs:
            shutil.copy(spec, cls._PATH_SPECS +"/" + spec.name)
            cls.ensure_specs_exist()
            pass
            
        # 更新版本文件
        version_file = path / "VERSION"
        version_file.write_text(version, encoding="utf-8")

        return cls(path, **kwargs)

    @property
    def current_version(self) -> str:
        """获取当前语义化版本号"""
        return self._current_version
    
    def _read_version(self) -> str:
        """从VERSION文件读取版本号"""
        version_file = self.path / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
        return self._INVAID_VERSION_
    
    
    def update_version(self, new_version: str):
        """更新仓库版本号"""
        if not re.match(r"^\d+\.\d+\.\d+$", new_version):
            raise ValueError("版本号格式必须为X.X.X")
        
        # 更新版本文件
        version_file = self.path / "VERSION"
        version_file.write_text(new_version, encoding="utf-8")
        self._current_version = new_version
    
    def get_doc_path(self, doc_type: DocType, **context):

        template = self._PATH_TEMPLATES[doc_type]
        if "service" in context:
            service_name = context["service"]
            if not re.match(r"^[a-zA-Z0-9_-]+$", service_name):
                raise ValueError(f"Invalid service name: {service_name}")
        # 自动注入当前版本
        rel_path = template.format(
            version=self.current_version,
            **{k:v for k,v in context.items() if k != "version"}
        )
        return self.path / rel_path  # 生成绝对路径
    
    def ensure_directory(self, doc_type: DocType, **context):
        """确保所有父目录存在"""
        full_path = self.get_doc_path(doc_type, **context)
        full_path.parent.mkdir(parents=True, exist_ok=True)  # 递归创建目录
        return full_path

    def ensure_specs_exist(self):
        """确保所有规范文件存在"""
        for spec in self._PATH_SPECS_FILES:
            if not (self.path / spec).exists():
                raise FileNotFoundError(f"未找到规范文件：{spec}")
    def print_path(self):
        """打印当前repo下所有文件夹和文件路径"""
        for path in self.path.iterdir():
            print(path)

    

class AICODocument(Document):
    """
    AICO领域文档模型
    职责：
    - 封装文档元数据（类型、版本、评审记录等）
    - 提供文档创建的工厂方法
    - 维护文档内容与存储路径的映射关系
    - 实现文档与持久化存储的交互
    """
    content: str
    path: Path
    doc_type: DocType
    version: str
    components: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        repo: AICORepo,
        doc_type: DocType,
        content: str,
        components: list = None,
        **context
    ) -> "AICODocument":
        """创建新文档实例"""
        if components:
            for comp in components:
                comp_name = comp.get("name", "")
                if not re.match(r"^[a-zA-Z0-9_-]+$", comp_name):
                    raise ValueError(f"Invalid component name: {comp_name}")
        
        path = repo.get_doc_path(doc_type, **context)
        doc = cls(
            content=content,
            path=path,
            doc_type=doc_type,
            version=repo.current_version,
            metadata=context
        )
        
        # 确保目录存在
        repo.ensure_directory(doc_type, **context)
        
        # 持久化存储
        doc.to_path()  # 调用父类的保存方法
        
        # 更新搜索索引
        # await self._cache_document_metadata(doc)
        
        return doc
    
    def get_metadata(self) -> dict:
        return {
            "doc_type": self.doc_type.value,
            "version": self.version,
            "path": str(self.path.relative_to(self.repo.path))
        }
    
    def rag_key(self) -> str:
        """实现RAGObject接口，提供检索用的文本内容"""
        return f"{self.doc_type.value}_{self.version}\n{self.content}"

class AICOTemplate:
    """
    AICO文档模板引擎
    职责：
    - 根据文档类型生成符合规范的初始内容
    - 维护各类型文档的Markdown模板
    - 处理模板变量的插值替换
    - 保证输出内容符合AICO文档规范
    """
    
    @classmethod
    def generate(cls, doc_type: DocType, params: dict) -> str:
        required_fields = {
            DocType.TECH_ARCH: ["version", "components"],
            DocType.USER_STORY: ["req_id", "scenario"],
            # 其他文档类型的必填字段...
        }
        
        if missing := [f for f in required_fields.get(doc_type, []) if f not in params]:
            raise ValueError(f"缺少必要参数: {missing}")
        
        generator = {
            DocType.USER_STORY: cls._user_story_template,
            DocType.TECH_ARCH: cls._tech_arch_template,
            DocType.PRD: cls._prd_template,
            DocType.SERVICE_DESIGN: cls._service_design_template,
            DocType.TEST_CASE_DESIGN: cls._test_case_template,
            DocType.BIZ_REQUIREMENT: cls._requirement_analysis_template,
            DocType.API_DESIGN: cls._api_spec_template
        }.get(doc_type, cls._default_template)
        return generator(params)
    
    @staticmethod
    def _default_template(data: dict) -> str:
        """默认模板返回空内容避免异常"""
        return ""
    
    @staticmethod
    def _user_story_template(data: dict) -> str:
        """用户故事模板"""
        content = [
            f"# 用户故事 - {data['req_id']}",
            f"**版本**: {data['version']}",
            f"**状态**: {data.get('status', '草案')}",
            "## 用户场景",
            data["scenario"],
            "## 验收标准",
            "\n".join(f"- {criteria}" for criteria in data["acceptance_criteria"])
        ]
        return "\n\n".join(content)
    
    @staticmethod
    def _tech_arch_template(data: dict) -> str:
        """技术架构模板"""
        components = "\n".join(
            f"- {comp['name']}: {comp['description']}" 
            for comp in data["components"]
        )
        return (
            f"# 技术架构文档 - {data['version']}\n"
            "## 架构组件\n"
            f"{components}\n"
            "## 架构图\n"
            f"![架构图]({data['diagram_url']})"
        )
    
    @staticmethod
    def _prd_template(data: dict) -> str:
        """产品需求文档模板"""
        features = "\n\n".join(
            f"### {feat['title']}\n{feat['description']}" 
            for feat in data["features"]
        )
        return f"# 产品需求文档\n\n## 功能列表\n\n{features}"
    
    @staticmethod
    def _service_design_template(data: dict) -> str:
        """服务设计模板"""
        apis = "\n".join(
            f"- {api['method']} {api['path']}: {api['description']}"
            for api in data["apis"]
        )
        return (
            f"# {data['service_name']}服务设计\n"
            "## 接口规范\n"
            f"{apis}"
        )
    
    @staticmethod
    def _test_case_template(data: dict) -> str:
        """测试用例模板"""
        cases = []
        for case in data["cases"]:
            steps = "\n".join(
                f"{step['num']}. {step['action']} -> 预期结果: {step['expected']}"
                for step in case["steps"]
            )
            cases.append(
                f"## {case['title']}\n"
                f"**前置条件**: {case['preconditions']}\n"
                f"**测试步骤**:\n{steps}"
            )
        return "\n\n".join(cases)
    
    @staticmethod
    def _requirement_analysis_template(data: dict) -> str:
        """需求分析模板"""
        stories = "\n".join(
            f"- {story['title']}: {story['description']}"
            for story in data["user_stories"]
        )
        return (
            f"# 需求分析报告 - {data['req_id']}\n"
            "## 业务目标\n"
            f"{data['business_goal']}\n"
            "## 用户故事\n"
            f"{stories}"
        )
    
    @staticmethod
    def _api_spec_template(data: dict) -> str:
        """API规范模板"""
        apis = "\n".join(
            f"### {api['method']} {api['path']}\n"
            f"- 功能: {api['description']}\n"
            f"- 请求参数: {api.get('params', '无')}\n"
            f"- 响应格式: {api.get('response', 'application/json')}"
            for api in data["apis"]
        )
        return (
            f"# {data['service']}服务接口规范\n"
            f"**版本**: {data.get('version', '1.0.0')}\n\n"
            "## 接口列表\n"
            f"{apis}"
        )

class AICODocManager:
    """
    AICO文档服务协调器
    职责：
    - 管理文档全生命周期（创建、读取、更新、删除）
    - 维护文档搜索索引
    - 实现基于语义的文档检索
    - 管理文档版本历史
    - 协调仓库、模板、存储等组件的交互
    """
    
    def __init__(self, repo: Union[Path, AICORepo], specs: List[Path] = None, embed_model=None, llm=None):
        # 统一处理路径输入
        if isinstance(repo, Path):
            if repo.exists():
                self.repo = AICORepo(repo)
            else:
                assert specs is not None, "specs参数不能为空"
                self.repo = AICORepo.init_project(repo, specs)
        elif isinstance(repo, AICORepo):
            self.repo = repo
        else:
            raise TypeError("repo参数必须是Path或AICORepo类型")     

        self.search_engine = self._init_search_engine(embed_model, llm)
    
    @classmethod
    def from_path(cls, path: Path, **kwargs):
        """替代构造函数：从路径初始化"""
        return cls(AICORepo(path), **kwargs)
    
    @classmethod
    def from_repo(cls, repo: AICORepo, **kwargs):
        """替代构造函数：从已有仓库初始化""" 
        return cls(repo, **kwargs)
    
    def _init_search_engine(self, embed_model = None, llm = None) -> SimpleEngine:
        """初始化文档检索引擎"""
        
        documents = [
            doc for doc in self.repo.get_text_documents()
            if isinstance(doc, AICODocument)
        ]


        if embed_model is None:
            embed_model = get_embedding()

        engine = SimpleEngine.from_objs(
            objs=documents,
            retriever_configs=[FAISSRetrieverConfig()],
            embed_model=embed_model,  # 确保传入正确类型的embed_model
            llm=llm
        )
        return engine
    
    async def create_document(self, doc_type: DocType, **context):
        # 添加文档类型校验
        if not isinstance(doc_type, DocType):
            raise ValueError(f"Invalid document type: {type(doc_type)}")
        
        # 自动添加当前版本到上下文
        context = {
            **context,
            "version": self.repo.current_version  # 统一管理版本
        }
        content = AICOTemplate.generate(doc_type, context)
        
        doc = AICODocument.create(
            repo=self.repo,
            doc_type=doc_type,
            content=content,
            **context
        )
        
        # 确保目录存在
        self.repo.ensure_directory(doc_type, **context)
        
        # 持久化存储
        full_path = doc.path  # 直接使用get_doc_path生成的绝对路径
        full_path.write_text(doc.content)
    
        # 更新搜索索引
        self.search_engine.add_objs([doc])
        
        # 缓存元数据
        # await self._cache_document_metadata(doc)
        
        return doc
    
    
    async def get_document(self, doc_type: DocType, context: dict = None) -> Optional[AICODocument]:
        """获取指定文档"""
        path = self.repo.get_doc_path(doc_type, **(context or {}))
        full_path = self.repo.path / path
        if not full_path.exists():
            return None
        return AICODocument(
            content=full_path.read_text(encoding="utf-8"),
            path=path,
            doc_type=doc_type,
            version=self.repo.current_version,
            metadata=context
        )
    
    async def search_documents(self, query: str, doc_types: List[DocType] = None, limit: int = 5) -> List[dict]:
        """语义化文档搜索
        
        Args:
            query: 搜索查询语句
            doc_types: 文档类型过滤列表,为空则搜索所有类型
            limit: 返回结果数量限制
            
        Returns:
            List[dict]: 搜索结果列表,每个结果包含content、metadata和score
        """
        # 从上下文看,search_engine是SimpleEngine实例
        # aretrieve返回的是NodeWithScore列表
        nodes = await self.search_engine.aretrieve(query)
        
        results = []
        for node in nodes:
            # 检查文档类型是否匹配过滤条件
            if doc_types and DocType(node.metadata["doc_type"]) not in doc_types:
                continue
            print(node.metadata)
            print(node.text)
            print(node.score)
            results.append({
                "content": node.text, 
                "metadata": node.metadata,
                "score": node.score
            })
            
            if len(results) >= limit:
                break
                
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    
    def get_specification(self, spec_type: DocType) -> str:
        """获取项目规范内容"""
        spec_path = self.repo.get_doc_path(spec_type)
        full_path = self.repo.path / spec_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"未找到规范文件：{spec_type.value}")