"""
AICO规范管理服务（V2）

核心原则：
1. 全局规范与项目规范完全独立管理
2. 全局规范强制同步时不修改项目规范
3. 项目规范初始化仅提供模板
4. 规范使用方自行处理规范优先级
"""

from pathlib import Path
import hashlib
import shutil
from datetime import datetime
from typing import Optional

class SpecService:
    """规范管理服务（独立管理全局/项目规范）"""
    
    GLOBAL_SPEC_DIR = Path("docs/aico/specs")
    PROJECT_SPEC_DIR_NAME = "specs"
    
    # 支持的规范类型（扩展时在此注册）
    SPEC_TYPES = {
        "ea_design": "架构设计规范",
        "req_tracking": "需求跟踪规范"
    }

    def __init__(self, project_root: Optional[str] = None):
        """初始化规范服务
        
        Args:
            project_root: 项目根目录路径，None表示仅使用全局规范
        """
        self.project_spec_dir = Path(project_root)/self.PROJECT_SPEC_DIR_NAME if project_root else None

    def get_global_spec(self, spec_type: str) -> str:
        """获取全局规范内容"""
        self._validate_spec_type(spec_type)
        spec_file = self.GLOBAL_SPEC_DIR / f"{spec_type}_spec.md"
        return spec_file.read_text() if spec_file.exists() else ""

    def get_project_spec(self, spec_type: str) -> str:
        """获取项目规范内容"""
        self._validate_spec_type(spec_type)
        if not self.project_spec_dir:
            return ""
            
        spec_file = self.project_spec_dir / f"{spec_type}_spec.md"
        return spec_file.read_text() if spec_file.exists() else ""

    def sync_global_spec(self, spec_type: str) -> bool:
        """同步全局规范到项目目录（仅初始化时使用）"""
        self._validate_spec_type(spec_type)
        
        if not self.project_spec_dir:
            raise RuntimeError("项目未初始化")
            
        global_file = self.GLOBAL_SPEC_DIR / f"{spec_type}_spec.md"
        project_file = self.project_spec_dir / f"{spec_type}_spec.md"
        
        # 仅当项目规范不存在时同步
        if not project_file.exists() and global_file.exists():
            self._backup_file(project_file)
            shutil.copy(global_file, project_file)
            return True
        return False

    def init_project_spec(self, spec_type: str) -> Path:
        """初始化项目规范模板"""
        self._validate_spec_type(spec_type)
        
        if not self.project_spec_dir:
            raise RuntimeError("项目未初始化")
            
        project_file = self.project_spec_dir / f"{spec_type}_spec.md"
        if not project_file.exists():
            project_file.write_text(
                "# 项目专属规范模板\n\n"
                "## 接口规范\n"
                "- 必须包含请求/响应示例\n"
                "- 错误码需明确说明\n\n"
                "## 数据规范\n"
                "- 时间格式统一使用ISO 8601\n"
                "- 金额单位统一为人民币分\n\n"
                "## 其他要求\n"
                "请在此补充项目特定规范...\n"
            )
        return project_file

    def _validate_spec_type(self, spec_type: str):
        """校验规范类型有效性"""
        if spec_type not in self.SPEC_TYPES:
            raise ValueError(f"无效规范类型: {spec_type}。可用类型: {list(self.SPEC_TYPES.keys())}")

    def _backup_file(self, file_path: Path):
        """创建文件备份"""
        if file_path.exists():
            backup_name = f"{file_path.stem}_bak_{datetime.now().strftime('%Y%m%d%H%M')}{file_path.suffix}"
            shutil.copy(file_path, file_path.with_name(backup_name)) 