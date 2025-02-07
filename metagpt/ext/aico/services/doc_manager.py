from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from metagpt.utils.embedding import get_embedding
from metagpt.provider.base_llm import BaseLLM
from metagpt.utils.redis import Redis
from metagpt.config2 import config
from metagpt.const import DEFAULT_MAX_TOKENS
from metagpt.rag.engines.simple import SimpleEngine
from metagpt.rag.schema import FAISSIndexConfig, FAISSRetrieverConfig

class DocType(str, Enum):
    """AICO文档类型(按照README_AICO_DOC_VERSION_CN.md定义)"""
    # PM文档
    PROJECT_TRACKING = "project_tracking"      # 项目跟踪表
    VERSION_PLAN = "version_plan"             # 版本规划文件
    SPEC_PM = "spec_pm"                       # PM管理规范
    SPEC_BA = "spec_ba"                       # BA规范
    SPEC_EA = "spec_ea"                       # EA规范
    SPEC_PRD = "spec_prd"                     # PRD规范
    SPEC_DEV = "spec_dev"                     # 开发规范
    SPEC_QA = "spec_qa"                       # 测试规范
    REQUIREMENT_RAW = "requirement_raw"        # 原始需求
    
    # BA文档
    BUSINESS_ARCH = "business_arch"           # 业务架构文档
    REQUIREMENT_ANALYZED = "requirement_analyzed" # 需求分析报告
    USER_STORY = "user_story"                 # 用户故事
    
    # EA文档
    TECH_ARCH = "tech_arch"                   # 技术架构文档
    TECH_REQUIREMENT = "tech_requirement"      # 技术需求分析
    
    # PRD文档
    PRD = "prd"                              # 产品设计文档
    
    # DEV文档
    SERVICE_DESIGN = "service_design"         # 服务设计文档
    API_SPEC = "api_spec"                     # 接口规范
    
    # QA文档
    TEST_CASE = "test_case"                   # 测试用例
    TEST_REPORT = "test_report"               # 测试报告

class DocMetadata(BaseModel):
    """文档元数据"""
    doc_id: str
    doc_type: str
    version: str
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    extra: Dict = Field(default_factory=dict)

class DocBaseTemplate:
    """基础文档模板"""
    
    @staticmethod
    def add_header(title: str, version: str = "") -> str:
        """添加文档头"""
        content = f"# {title}\n\n"
        if version:
            content += f"**版本**: {version}\n"
        content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return content

class DocTemplate(DocBaseTemplate):
    """AICO文档模板"""
    
    @staticmethod
    def user_story(version: str, stories: List[Dict]) -> str:
        """用户故事文档(按照BA规范)"""
        content = DocBaseTemplate.add_header("项目用户故事", version)
        
        for std_req_id, story_list in stories.items():
            content += f"## 标准需求 {std_req_id}\n"
            for story in story_list:
                content += f"### 用户故事 {story['story_id']}\n"
                content += f"**标题**: {story['title']}\n"
                content += f"**状态**: {story['status']}\n"
                content += f"**验收标准**:\n{story['acceptance_criteria']}\n\n"
        return content
    
    @staticmethod
    def requirement_analysis(req_id: str, analysis_result: Dict) -> str:
        """需求分析报告(按照BA规范)"""
        content = DocBaseTemplate.add_header(f"需求分析报告 - {req_id}")
        content += "## 业务需求说明\n\n"
        content += f"**需求编号**: {analysis_result['requirement_id']}\n"
        content += f"**需求描述**: {analysis_result['description']}\n"
        content += f"**业务流程**: {analysis_result['business_process']}\n\n"
        content += "## 用户故事\n\n"
        for story in analysis_result['user_stories']:
            content += f"### {story['title']}\n"
            content += f"**验收标准**: {story['acceptance_criteria']}\n\n"
        return content

class AICODocManager:
    """AICO文档管理器 - 统一处理文档存储、检索和管理"""
    
    def __init__(self, project_root: Path, llm: Optional[BaseLLM] = None):
        self.project_root = project_root
        self.llm = llm
        self.embedding = get_embedding()
        self.redis = Redis(config.redis)
        self.threshold = 0.1  # 相似度阈值
        
        # 初始化向量引擎
        self.engine = SimpleEngine.from_objs(
            objs=[],
            retriever_configs=[FAISSRetrieverConfig()],
            embed_model=self.embedding
        )
        
        # 确保目录存在
        self.docs_path = project_root / "docs"
        self.docs_path.mkdir(parents=True, exist_ok=True)
        
    def get_doc_path(self, doc_type: str, version: str, **kwargs) -> Path:
        """获取文档路径(按照AICO规范)"""
        base_paths = {
            # PM文档路径
            "PROJECT_TRACKING": "tracking/project_tracking.xlsx",
            "VERSION_PLAN": "VERSION",
            "SPEC_PM": "docs/specs/pm_guide.md",
            "SPEC_BA": "docs/specs/ba_guide.md", 
            "SPEC_EA": "docs/specs/ea_guide.md",
            "SPEC_PRD": "docs/specs/prd_guide.md",
            "SPEC_DEV": "docs/specs/dev_guide.md",
            "SPEC_QA": "docs/specs/qa_guide.md",
            "REQUIREMENT_RAW": "docs/requirements/raw",
            
            # 版本相关文档路径
            "BUSINESS_ARCH": f"docs/ea/biz_arch/{version}/biz_arch.md",
            "REQUIREMENT_ANALYZED": f"docs/requirements/analyzed/{version}/req-{{req_id}}",
            "USER_STORY": f"docs/requirements/analyzed/{version}/user_stories",
            "TECH_ARCH": f"docs/ea/tech_arch/{version}/tech_arch.md",
            "PRD": f"docs/design/prd/{version}/prd.md",
            "SERVICE_DESIGN": f"docs/design/services/{{service}}/{version}/service_design.md",
            "API_SPEC": f"docs/design/services/{{service}}/{version}/api_spec.yaml",
            "TEST_CASE": f"docs/design/tests/{{service}}/{version}/test_cases.md",
            "TEST_REPORT": f"releases/{version}/qa_report.md"
        }
        
        path_template = base_paths[doc_type]
        
        # 处理路径模板中的变量
        if kwargs:
            path_template = path_template.format(**kwargs)
            
        doc_path = self.project_root / path_template
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        return doc_path

    async def save_document(
        self,
        doc_type: str,
        content: str,
        version: str,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """保存文档"""
        # 生成文档ID
        doc_id = f"DOC-{doc_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建元数据
        meta = DocMetadata(
            doc_id=doc_id,
            doc_type=doc_type,
            version=version,
            **metadata or {}
        )
        
        # 保存文件
        doc_path = self.get_doc_path(doc_type, version, **kwargs)
        doc_path.write_text(content, encoding="utf-8")
        
        # 添加到向量库
        self.engine.add_objs([{
            "content": content,
            "metadata": meta.dict()
        }])
        
        # 缓存元数据
        await self.redis.set(
            f"doc:meta:{doc_id}",
            meta.json(),
            timeout_sec=3600
        )
        
        return doc_id

    async def read_document(
        self,
        doc_type: str,
        version: str = "latest",
        **kwargs
    ) -> Optional[str]:
        """读取文档"""
        doc_path = self.get_doc_path(doc_type, version, **kwargs)
        if not doc_path.exists():
            return None
        return doc_path.read_text(encoding="utf-8")

    async def search_similar(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        k: int = 4
    ) -> List[Dict]:
        """搜索相似文档"""
        results = []
        resp = await self.engine.aretrieve(query)
        
        for item in resp:
            if item.score < self.threshold:
                continue
                
            meta = item.metadata
            if doc_types and meta["doc_type"] not in doc_types:
                continue
                
            results.append({
                "content": item.content,
                "metadata": meta
            })
            
            if len(results) >= k:
                break
                
        return results

    async def get_doc_history(
        self,
        doc_type: str,
        doc_id: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[DocMetadata]:
        """获取文档历史版本"""
        pattern = f"doc:meta:DOC-{doc_type}-*"
        keys = await self.redis.keys(pattern)
        
        history = []
        for key in keys:
            meta_json = await self.redis.get(key)
            if not meta_json:
                continue
                
            meta = DocMetadata.parse_raw(meta_json)
            
            if doc_id and meta.doc_id != doc_id:
                continue
            if version and meta.version != version:
                continue
                
            history.append(meta)
            
        return sorted(history, key=lambda x: x.created_at, reverse=True)

    async def summarize_doc(self, content: str, max_words: int = 200) -> str:
        """生成文档摘要"""
        if not self.llm:
            return content[:max_words]
            
        prompt = f"""请将以下文档内容总结为不超过{max_words}字的摘要:

{content}

摘要:"""
        
        summary = await self.llm.aask(prompt)
        return summary 