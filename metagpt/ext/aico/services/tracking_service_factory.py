from .excel_tracking_service import ExcelTrackingService
from .base_tracking_service import ITrackingService

class TrackingServiceFactory:
    @classmethod
    def create(cls, file_path: Path, env: str = "prod") -> ITrackingService:
        if env == "test":
            from metagpt.ext.aico.services.mock_tracking_service import MockTrackingService
            return MockTrackingService(file_path)
        return ExcelTrackingService(file_path) 