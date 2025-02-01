from typing import Dict, List, Tuple, Type
from metagpt.roles.role import Role
from metagpt.actions import Action

class AICOBaseRole(Role):
    """AICO角色基类，提供增强的Action管理"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._action_map: Dict[str, Action] = {}
        self._init_actions()
        
    def _init_actions(self):
        """初始化Action（由子类实现）"""
        actions = self.get_actions()
        if not actions:
            return
            
        # 创建有序字典保持执行顺序
        self._action_map = {name: action() if isinstance(action, type) else action 
                          for name, action in actions}
        
        # 保持与MetaGPT原生set_actions的兼容
        super().set_actions(list(self._action_map.values()))
        
    def get_actions(self) -> List[Tuple[str, Type[Action]]]:
        """子类必须实现的抽象方法，返回(名称, Action)列表"""
        raise NotImplementedError("Subclasses must implement get_actions()")
        
    def get_action(self, name: str) -> Action:
        """通过名称获取Action"""
        return self._action_map.get(name)
        
    def set_actions(self, actions: List[Action]):
        """重写原生方法以保持映射同步"""
        # 警告：使用原生方法会破坏映射，建议子类通过get_actions定义
        raise RuntimeError("Use get_actions() instead for AICO roles")

