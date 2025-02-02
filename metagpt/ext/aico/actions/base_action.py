from datetime import datetime
from metagpt.actions import Action
from typing import Dict, Any
from pathlib import Path
import time
import re
from jsonschema import validate

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
        
        # 使用JSON Schema校验输出结构
        schema = {
            "type": "object",
            "properties": {
                "application_architecture": {"type": "object"},
                "technical_architecture": {"type": "object"},
                "data_architecture": {"type": "object"}
            },
            "required": ["application_architecture", "technical_architecture"]
        }
        validate(instance=result, schema=schema)
        
        # 检查版本号格式
        if not re.match(r"\d+\.\d+[a-z]?", result.get("version", "")):
            raise ValueError("版本号不符合语义化规范")
        
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

    def safe_save_workbook(self, wb, file_path: Path):
        """安全保存Excel文件"""
        try:
            for attempt in range(3):
                try:
                    wb.save(file_path)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)
            # 增加备份机制
            backup_path = file_path.with_name(f"backup_{file_path.name}")
            if backup_path.exists():
                backup_path.unlink()
            file_path.rename(backup_path)
            wb.save(file_path)
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
            raise 