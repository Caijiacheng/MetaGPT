def validate_raw_requirement(self, req_data: dict) -> bool:
    """校验原始需求记录完整性（文档5.2节）"""
    required_fields = ["file_path", "description", "source"]
    return all(field in req_data for field in required_fields)