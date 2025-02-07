from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

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

class DocManagerService:
    """AICO文档管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.template = DocTemplate
    
    def get_doc_path(self, doc_type: DocType, version: str = "", **kwargs) -> Path:
        """获取文档路径(按照目录结构规范2.0)"""
        base_paths = {
            # PM文档路径
            DocType.PROJECT_TRACKING: "tracking/project_tracking.xlsx",
            DocType.VERSION_PLAN: "VERSION",
            DocType.SPEC_PM: "docs/specs/pm_guide.md",
            DocType.SPEC_BA: "docs/specs/ba_guide.md",
            DocType.SPEC_EA: "docs/specs/ea_guide.md",
            DocType.SPEC_PRD: "docs/specs/prd_guide.md",
            DocType.SPEC_DEV: "docs/specs/dev_guide.md",
            DocType.SPEC_QA: "docs/specs/qa_guide.md",
            DocType.REQUIREMENT_RAW: "docs/requirements/raw",
            
            # 版本相关文档路径
            DocType.BUSINESS_ARCH: f"docs/ea/biz_arch/{version}/biz_arch.md",
            DocType.REQUIREMENT_ANALYZED: f"docs/requirements/analyzed/{version}/req-{{req_id}}",
            DocType.USER_STORY: f"docs/requirements/analyzed/{version}/user_stories",
            DocType.TECH_ARCH: f"docs/ea/tech_arch/{version}/tech_arch.md",
            DocType.PRD: f"docs/design/prd/{version}/prd.md",
            DocType.SERVICE_DESIGN: f"docs/design/services/{{service}}/{version}/service_design.md",
            DocType.API_SPEC: f"docs/design/services/{{service}}/{version}/api_spec.yaml",
            DocType.TEST_CASE: f"docs/design/tests/{{service}}/{version}/test_cases.md",
            DocType.TEST_REPORT: f"releases/{version}/qa_report.md"
        }
        
        path_template = base_paths[doc_type]
        
        # 处理路径模板中的变量
        if kwargs:
            path_template = path_template.format(**kwargs)
            
        doc_path = self.project_root / path_template
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        return doc_path
    
    def save_document(self, doc_type: DocType, content: str, version: str = "", **kwargs) -> Path:
        """保存文档"""
        file_path = self.get_doc_path(doc_type, version, **kwargs)
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def read_document(self, doc_type: DocType, version: str = "", **kwargs) -> str:
        """读取文档"""
        file_path = self.get_doc_path(doc_type, version, **kwargs)
        return file_path.read_text(encoding="utf-8") 