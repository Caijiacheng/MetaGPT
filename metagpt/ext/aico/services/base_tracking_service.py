from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

class ITrackingService(ABC):
    @abstractmethod
    def add_raw_requirement(self, file_path: str, req_type: str) -> bool:
        pass
    
    @abstractmethod
    def get_pending_requirements(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def update_task_status(self, task_id: str, status: str) -> bool:
        pass 