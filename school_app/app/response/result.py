# response/result.py
from typing import Dict, Any, Optional

class Result:
    def __init__(self, code: int, message: str, extra: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.extra = extra or {}

    def http_response(self):
        return {
            "code": self.code,
            "message": self.message,
            "result": self.extra
        }
