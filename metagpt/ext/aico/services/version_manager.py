from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AICOVersionManager:
    """语义化版本管理服务（增强初始化逻辑）"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.current_version = self._load_or_init_version()
        
    def _load_or_init_version(self) -> str:
        """加载或初始化版本号"""
        version_file = self.project_root / "VERSION"
        
        if version_file.exists():
            version = version_file.read_text().strip()
            self.validate_version(version)
            return version
            
        # 新项目初始化逻辑
        initial_version = "0.1.0"
        version_file.write_text(initial_version + "\n")
        return initial_version
    
    @staticmethod
    def validate_version(version: str):
        """校验版本号格式"""
        parts = version.split('.')
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"非法版本号格式: {version}")
    
    def generate_first_release(self) -> str:
        """生成首个正式版本（从0.1.0→1.0.0）"""
        if self.current_version != "0.1.0":
            raise ValueError("只能在初始化版本生成首个正式版本")
            
        self.current_version = "1.0.0"
        self._update_version_file()
        return self.current_version
    
    def bump(self, change_type: str) -> str:
        """生成新版本并更新文件"""
        major, minor, patch = map(int, self.current_version.split('.'))
        
        if change_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif change_type == "minor":
            minor += 1
            patch = 0
        elif change_type == "patch":
            patch += 1
        else:
            raise ValueError(f"无效变更类型: {change_type}")
            
        new_version = f"{major}.{minor}.{patch}"
        self.current_version = new_version
        self._update_version_file()
        return new_version
    
    def _update_version_file(self):
        """更新VERSION文件"""
        version_file = self.project_root / "VERSION"
        version_file.write_text(self.current_version + "\n")

def get_current_version(project_root: Path) -> str:
    """从VERSION文件获取当前版本"""
    version_file = project_root / "VERSION"
    if not version_file.exists():
        return "1.0.0"
    
    with open(version_file, "r") as f:
        version = f.read().strip()
    
    # 格式校验
    try:
        AICOVersionManager.from_version(version)
        return version
    except ValueError:
        logger.error(f"VERSION文件格式错误: {version}")
        return "1.0.0"

def update_version_file(project_root: Path, new_version: str):
    """更新VERSION文件"""
    version_file = project_root / "VERSION"
    with open(version_file, "w") as f:
        f.write(new_version + "\n")
    logger.info(f"版本文件已更新: {new_version}") 