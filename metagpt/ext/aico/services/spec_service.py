"""
规范管理服务（V3）

核心改进：
1. 全局规范路径由环境配置传入
2. 规范类型独立管理，支持差异化初始化
3. 严格分离同步机制（global强制覆盖 vs project初始化）
"""

from pathlib import Path
import shutil
from datetime import datetime
from typing import Optional, Dict

class BaseSpec:
    """规范基类"""
    def __init__(self, spec_type: str):
        self.spec_type = spec_type
        self.project_template = self._default_template()
        
    def _default_template(self) -> str:
        """默认项目规范模板"""
        return """# 项目专属规范模板\n请在此补充项目特定规范..."""
    
    def init_project_spec(self, project_spec_dir: Path) -> Path:
        """初始化项目规范文件"""
        spec_file = project_spec_dir / f"{self.spec_type}_spec.md"
        if not spec_file.exists():
            spec_file.write_text(self.project_template, encoding="utf-8")
        return spec_file

class EADesignSpec(BaseSpec):
    """架构设计规范"""
    def __init__(self):
        super().__init__("ea_design")
        self.project_template = """# 项目架构设计规范

## 接口规范
- 必须包含请求/响应示例
- 错误码需明确说明

## 数据规范
- 时间格式统一使用ISO 8601
- 金额单位统一为人民币分

## 扩展要求
请在此补充项目特有架构规范..."""

class ProjectTrackingSpec(BaseSpec):
    """需求跟踪规范""" 
    def __init__(self):
        super().__init__("req_tracking")
        self.project_template = """# 项目需求跟踪规范

## 状态流转规则
```mermaid
stateDiagram
    [*] --> new
    new --> parsed
    parsed --> implemented
    implemented --> [*]
```

## 版本管理
- 主版本：架构变更
- 次版本：需求变更
- 修订号：文档修正"""

class SpecService:
    """规范管理服务"""
    
    # 规范类型注册
    SPEC_CLASSES = {
        "ea_design": EADesignSpec,
        "project_tracking": ProjectTrackingSpec
    }

    def __init__(self, global_spec_root: Path, project_root: Optional[Path] = None):
        """
        Args:
            global_spec_root: 全局规范根目录（从环境配置传入）
            project_root: 项目根目录（可选）
        """
        self.global_spec_root = global_spec_root
        self.project_spec_root = project_root / "specs" if project_root else None

    def sync_global_spec(self, spec_type: str) -> bool:
        """同步全局规范（强制覆盖项目规范）"""
        if spec_type not in self.SPEC_CLASSES:
            raise ValueError(f"无效规范类型: {spec_type}")
            
        if not self.project_spec_root:
            raise RuntimeError("项目未初始化")
            
        global_spec = self.global_spec_root / f"{spec_type}_spec.md"
        project_spec = self.project_spec_root / f"{spec_type}_spec.md"
        
        if not global_spec.exists():
            return False
            
        # 强制覆盖逻辑（无论项目规范是否存在）
        self._backup_file(project_spec)
        shutil.copy(global_spec, project_spec)
        return True

    def init_project_spec(self, spec_type: str) -> Path:
        """初始化项目规范（仅生成模板，不涉及同步）"""
        if spec_type not in self.SPEC_CLASSES:
            raise ValueError(f"无效规范类型: {spec_type}")
            
        if not self.project_spec_root:
            raise RuntimeError("项目未初始化")
            
        # 仅当项目规范不存在时初始化
        spec_file = self.project_spec_root / f"{spec_type}_spec.md"
        if not spec_file.exists():
            spec_class = self.SPEC_CLASSES[spec_type]()
            return spec_class.init_project_spec(self.project_spec_root)
        return spec_file

    def get_global_spec(self, spec_type: str) -> str:
        """获取全局规范内容"""
        if spec_type not in self.SPEC_CLASSES:
            raise ValueError(f"无效规范类型: {spec_type}")
            
        spec_file = self.global_spec_root / f"{spec_type}_spec.md"
        return spec_file.read_text() if spec_file.exists() else ""

    def get_project_spec(self, spec_type: str) -> str:
        """获取项目规范内容""" 
        if spec_type not in self.SPEC_CLASSES:
            raise ValueError(f"无效规范类型: {spec_type}")
            
        if not self.project_spec_root:
            return ""
            
        spec_file = self.project_spec_root / f"{spec_type}_spec.md"
        return spec_file.read_text() if spec_file.exists() else ""

    def _backup_file(self, file_path: Path):
        """创建文件备份"""
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            backup_name = f"{file_path.stem}_bak_{timestamp}{file_path.suffix}"
            shutil.copy(file_path, file_path.with_name(backup_name)) 