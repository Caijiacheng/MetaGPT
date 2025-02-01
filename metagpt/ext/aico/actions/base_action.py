from datetime import datetime
from metagpt.actions import Action
from typing import Dict, Any

class AICOBaseAction(Action):
    """AICO Action基类，提供通用功能"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
        
    async def validate_input(self, input_data: Dict) -> bool:
        """输入数据验证（由子类实现）"""
        raise NotImplementedError("Subclasses must implement validate_input()")
        
    async def post_process(self, result: Dict) -> Dict:
        """结果后处理（默认实现）"""
        result.update({
            "action_name": self.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        })
        return result
        
    async def run(self, *args, **kwargs):
        """重写run方法加入验证和后处理"""
        input_data = self._prepare_input(*args, **kwargs)
        if not await self.validate_input(input_data):
            raise ValueError("Invalid input data")
            
        raw_result = await self._run_impl(input_data)
        return await self.post_process(raw_result)
        
    async def _run_impl(self, input_data: Dict) -> Dict:
        """实际执行逻辑（由子类实现）"""
        raise NotImplementedError("Subclasses must implement _run_impl()")
        
    def _prepare_input(self, *args, **kwargs) -> Dict:
        """将输入转换为字典格式"""
        # 默认实现，子类可重写
        if args:
            return args[0] if isinstance(args[0], dict) else {}
        return kwargs 