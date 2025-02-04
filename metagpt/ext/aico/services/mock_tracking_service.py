from pathlib import Path
from typing import Dict, List
from .base_tracking_service import ITrackingService

class MockTrackingService(ITrackingService):
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data = {
            "raw_reqs": [],
            "requirements": [],
            "user_stories": [],
            "tasks": []
        }
    
    def add_raw_requirement(self, file_path: str, req_type: str) -> bool:
        self.data["raw_reqs"].append({
            "file": file_path,
            "type": req_type,
            "status": "待分析"
        })
        return True
    
    def get_pending_requirements(self) -> List[Dict]:
        return [r for r in self.data["raw_reqs"] 
               if r["status"] in ["待分析", "分析中"]]
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        # 模拟实现...
        return True 