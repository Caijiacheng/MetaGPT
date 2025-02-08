from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum
from pydantic import Field

from metagpt.document import Document, Repo
from metagpt.utils.embedding import get_embedding
from metagpt.provider.base_llm import BaseLLM
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
    REQUIREMENT_RAW = "requirement_raw"
    BUSINESS_ARCH = "business_arch"
    REQUIREMENT_ANALYZED = "requirement_analyzed"
    USER_STORY = "user_story"
    TECH_ARCH = "tech_arch"
    TECH_REQUIREMENT = "tech_requirement"
    PRD = "prd"
    SERVICE_DESIGN = "service_design"
    API_SPEC = "api_spec"
    TEST_CASE = "test_case"
    TEST_REPORT = "test_report"

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
    
    _PATH_TEMPLATES = {
        DocType.PROJECT_TRACKING: "tracking/project_tracking.xlsx",
        DocType.VERSION_PLAN: "VERSION",
        DocType.SPEC_PM: "docs/specs/pm_guide.md",
        DocType.SPEC_BA: "docs/specs/ba_guide.md",
        DocType.SPEC_EA: "docs/specs/ea_guide.md",
        DocType.SPEC_PRD: "docs/specs/prd_guide.md",
        DocType.SPEC_DEV: "docs/specs/dev_guide.md",
        DocType.SPEC_QA: "docs/specs/qa_guide.md",
        DocType.REQUIREMENT_RAW: "docs/requirements/raw/{req_id}.md",
        DocType.BUSINESS_ARCH: "docs/ea/biz_arch/{version}/biz_arch.md",
        DocType.REQUIREMENT_ANALYZED: "docs/requirements/analyzed/{version}/req-{req_id}/analysis.md",
        DocType.USER_STORY: "docs/requirements/analyzed/{version}/user_stories.md",
        DocType.TECH_ARCH: "docs/ea/tech_arch/{version}/tech_arch.md",
        DocType.TECH_REQUIREMENT: "docs/requirements/analyzed/{version}/req-{req_id}/tech_analysis.md",
        DocType.PRD: "docs/design/prd/{version}/prd.md",
        DocType.SERVICE_DESIGN: "docs/design/services/{service}/{version}/service_design.md",
        DocType.API_SPEC: "docs/design/services/{service}/{version}/api_spec.yaml",
        DocType.TEST_CASE: "docs/design/tests/{service}/{version}/test_cases.md",
        DocType.TEST_REPORT: "releases/{version}/qa_report.md"
    }
    
    def __init__(self, path: Path):
        super().__init__(path=path)
        self._current_version = self._read_version()
    
    @property
    def current_version(self) -> str:
        """获取当前语义化版本号"""
        return self._current_version
    
    def _read_version(self) -> str:
        """从VERSION文件读取版本号"""
        version_file = self.path / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
        return "0.0.0"
    
    def update_version(self, new_version: str):
        """更新仓库版本号"""
        version_file = self.path / "VERSION"
        version_file.write_text(new_version, encoding="utf-8")
        self._current_version = new_version
    
    def get_doc_path(self, doc_type: DocType, **context) -> Path:
        """生成符合AICO规范的文档路径"""
        template = self._PATH_TEMPLATES[doc_type]
        formatted = template.format(version=self.current_version, **context)
        return Path(formatted)
    
    def ensure_directory(self, doc_type: DocType, **context):
        """确保文档目录存在"""
        doc_path = self.get_doc_path(doc_type, **context)
        full_path = self.path / doc_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _classify_document(self, path: Path) -> str:
        """根据路径分类文档类型"""
        rel_path = str(path.relative_to(self.path))
        if "specs/" in rel_path:
            return "specs"
        if "requirements/" in rel_path:
            return "requirements"
        if "design/" in rel_path:
            return "design"
        if "tracking/" in rel_path or "releases/" in rel_path:
            return "operations"
        return "others"

class AICODocument(Document):
    """
    AICO领域文档模型
    职责：
    - 封装文档元数据（类型、版本、评审记录等）
    - 提供文档创建的工厂方法
    - 维护文档内容与存储路径的映射关系
    - 实现文档与持久化存储的交互
    """
    doc_type: DocType = Field(default=DocType.PROJECT_TRACKING)
    version: str = Field(default="latest")
    reviews: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        repo: AICORepo,
        doc_type: DocType,
        content: str,
        **context
    ) -> "AICODocument":
        """创建新文档实例"""
        path = repo.get_doc_path(doc_type, **context)
        return cls(
            content=content,
            path=path,
            doc_type=doc_type,
            version=repo.current_version,
            metadata=context
        )

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
    def generate(cls, doc_type: DocType, data: dict) -> str:
        """生成文档内容模板"""
        generator = {
            DocType.USER_STORY: cls._user_story_template,
            DocType.TECH_ARCH: cls._tech_arch_template,
            DocType.PRD: cls._prd_template,
            DocType.SERVICE_DESIGN: cls._service_design_template,
            DocType.TEST_CASE: cls._test_case_template,
            DocType.REQUIREMENT_ANALYZED: cls._requirement_analysis_template
        }.get(doc_type, cls._default_template)
        return generator(data)
    
    @staticmethod
    def _default_template(data: dict) -> str:
        """默认模板"""
        return f"# {data.get('title', 'Untitled Document')}\n\n{data.get('content', '')}"
    
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

class AICODocManager:
    """
    AICO文档服务协调器
    职责：
    - 管理文档全生命周期（创建、读取、更新、删除）
    - 维护文档搜索索引
    - 实现基于语义的文档检索
    - 管理文档版本历史
    - 与LLM集成生成文档摘要
    - 协调仓库、模板、存储等组件的交互
    """
    
    def __init__(self, repo: AICORepo, llm: Optional[BaseLLM] = None):
        self.repo = repo
        self.llm = llm
        self.redis = Redis(config.redis)
        self.search_engine = self._init_search_engine()
    
    def _init_search_engine(self) -> SimpleEngine:
        """初始化文档检索引擎"""
        documents = [
            {
                "content": doc.content,
                "metadata": {
                    "doc_type": doc.doc_type.value,
                    "version": doc.version,
                    "path": str(doc.path.relative_to(self.repo.path))
                }
            }
            for doc in self.repo.get_text_documents()
            if isinstance(doc, AICODocument)
        ]
        return SimpleEngine.from_objs(
            objs=documents,
            retriever_configs=[FAISSRetrieverConfig()],
            embed_model=get_embedding()
        )
    
    async def create_document(self, doc_type: DocType, **context) -> AICODocument:
        """创建并存储新文档"""
        # 生成内容
        content = AICOTemplate.generate(doc_type, context)
        
        # 创建文档对象
        doc = AICODocument.create(
            repo=self.repo,
            doc_type=doc_type,
            content=content,
            **context
        )
        
        # 确保目录存在
        self.repo.ensure_directory(doc_type, **context)
        
        # 持久化存储
        self.repo.set(str(doc.path.relative_to(self.repo.path)), doc.content)
        
        # 更新搜索索引
        self.search_engine.add_objs([{
            "content": doc.content,
            "metadata": {
                "doc_type": doc_type.value,
                "version": self.repo.current_version,
                "path": str(doc.path.relative_to(self.repo.path))
            }
        }])
        
        # 缓存元数据
        await self._cache_document_metadata(doc)
        
        return doc
    
    async def _cache_document_metadata(self, doc: AICODocument):
        """缓存文档元数据到Redis"""
        await self.redis.set(
            f"doc:{doc.doc_type}:{doc.version}",
            doc.json(),
            timeout_sec=3600*24  # 缓存24小时
        )
    
    async def get_document(self, doc_type: DocType, **context) -> Optional[AICODocument]:
        """获取指定文档"""
        path = self.repo.get_doc_path(doc_type, **context)
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
        """语义化文档搜索"""
        results = []
        retrieved = await self.search_engine.aretrieve(query)
        
        for item in retrieved:
            if doc_types and DocType(item.metadata["doc_type"]) not in doc_types:
                continue
            results.append({
                "content": item.content,
                "metadata": item.metadata,
                "score": item.score
            })
            if len(results) >= limit:
                break
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    async def get_version_history(self, doc_type: DocType) -> List[AICODocument]:
        """获取文档版本历史"""
        keys = await self.redis.keys(f"doc:{doc_type.value}:*")
        history = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                history.append(AICODocument.parse_raw(data))
        return sorted(history, key=lambda x: x.version, reverse=True)
    
    async def generate_summary(self, content: str, max_words: int = 200) -> str:
        """生成文档摘要"""
        if self.llm is None:
            return content[:max_words]
        
        prompt = (
            f"请为以下内容生成不超过{max_words}字的摘要：\n\n"
            f"{content}\n\n"
            "摘要："
        )
        return await self.llm.aask(prompt)
    
    def get_specification(self, spec_type: DocType) -> str:
        """获取项目规范内容"""
        spec_path = self.repo.get_doc_path(spec_type)
        full_path = self.repo.path / spec_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        # 回退到全局规范
        global_spec = Path(config.workspace.specs) / f"{spec_type.value}_spec.md"
        if global_spec.exists():
            return global_spec.read_text(encoding="utf-8")
        raise FileNotFoundError(f"未找到规范文件：{spec_type.value}")