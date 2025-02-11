from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

class AICOVersionManager:
    """语义化版本管理服务（增强初始化逻辑）"""
    
    def __init__(self, project_root: Path):
        """
        初始化版本管理服务，如果 project_root 不存在，则不进行版本文件操作，
        直接设置默认版本；如果存在，则加载或初始化 VERSION 文件。
        """
        self.project_root = project_root
        if self.project_root.exists():
            self.current_version = self._load_or_init_version()
        else:
            # 新项目未创建目录时，先设置一个默认版本，后续由项目初始化流程统一创建目录
            self.current_version = "0.1.0"
        
    @property
    def current(self) -> str:
        """
        增加只读属性 current，返回 current_version 用于向后兼容，
        避免在项目经理中调用 self.version_svc.current 时出错。
        """
        return self.current_version

    def _load_or_init_version(self):
        """
        尝试加载 VERSION 文件；如果不存在，则初始化文件并写入默认版本
        """
        version_file = self.project_root / "VERSION"
        initial_version = "0.1.0"
        # 确保目录存在
        version_file.parent.mkdir(parents=True, exist_ok=True)
        if version_file.exists():
            version = version_file.read_text().strip()
            return version if version else initial_version
        else:
            version_file.write_text(initial_version + "\n")
            return initial_version
    
    @classmethod
    def from_version(cls, version: str):
        # 创建临时对象用于验证版本格式
        temp = cls(Path("."))  # 使用有效路径初始化
        temp.validate_version(version)
        return temp

    def validate_version(self, input_version: str):
        """更健壮的版本校验"""
        parts = input_version.split('.')
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"无效版本格式: {input_version}")
        # 移除与current_version的对比检查（初始化时可能不一致是正常的）
    
    def generate_first_release(self) -> str:
        """生成首个正式版本（从0.1.0→1.0.0）"""
        if self.current_version != "0.1.0":
            raise ValueError("只能在初始化版本生成首个正式版本")
            
        self.current_version = "1.0.0"
        self._update_version_file()
        return self.current_version
    
    def bump(self, change_type: str) -> str:
        """
        根据 change_type（major/minor/patch），计算并更新版本号（示例实现）
        """
        old_version = self.current_version.split(".")
        if change_type == "major":
            new_version = f"{int(old_version[0]) + 1}.0.0"
        elif change_type == "minor":
            new_version = f"{old_version[0]}.{int(old_version[1]) + 1}.0"
        elif change_type == "patch":
            new_version = f"{old_version[0]}.{old_version[1]}.{int(old_version[2]) + 1}"
        else:
            raise ValueError("无效变更类型: " + change_type)
        # 更新版本文件（保证目录存在）
        version_file = self.project_root / "VERSION"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(new_version + "\n")
        self.current_version = new_version
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