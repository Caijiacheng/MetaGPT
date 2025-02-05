class VersionService:
    """语义化版本管理服务"""
    
    def __init__(self, initial_version: str = "1.0.0"):
        self.major, self.minor, self.patch = map(int, initial_version.split('.'))
        
    def bump_major(self) -> str:
        self.major += 1
        self.minor = 0
        self.patch = 0
        return self.current
    
    def bump_minor(self) -> str:
        self.minor += 1
        self.patch = 0
        return self.current
    
    def bump_patch(self) -> str:
        self.patch += 1
        return self.current
    
    @property
    def current(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}" 