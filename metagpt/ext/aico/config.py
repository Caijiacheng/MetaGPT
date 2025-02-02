from pathlib import Path
from metagpt.config2 import Config, merge_dict, WorkspaceConfig

class AICOConfig(Config):
    """AICO项目专属配置"""
    
    # 新增AICO特有配置项
    project_root: str = "./projects"
    tracking_filename: str = "ProjectTracking.xlsx"
    spec_paths: dict = {
        "ea_design": "docs/aico/specs/ea_design_spec.md",
        "project_tracking": "docs/aico/specs/project_tracking_spec.md"
    }
    
    # 继承MetaGPT基础配置并扩展
    workspace: WorkspaceConfig = WorkspaceConfig(
        project_root="./projects",
        docs="./docs",
        data="./data",
        tests="./tests",
        # AICO扩展目录
        specs="./docs/aico/specs",          # 规范文档
        tracking="./tracking",              # 跟踪文件
        architecture="./docs/ea",           # 架构文档
        requirements="./docs/requirements" # 需求文档
    )
    
    @classmethod
    def default(cls):
        """加载AICO默认配置"""
        base_config = super().default()
        
        # 合并AICO专属默认配置
        aico_workspace = {
            "workspace": {
                "project_root": str(Path(__file__).parent.parent / "projects"),
                "specs": "docs/aico/specs",
                "tracking": "tracking",
                "architecture": "docs/ea",
                "requirements": "docs/requirements"
            }
        }
        return cls(**merge_dict([base_config.model_dump(), aico_workspace]))

# 初始化配置实例
config = AICOConfig.default() 