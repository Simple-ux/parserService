import json
from datetime import datetime
from typing import Any, Optional

class ResponseBuilder:
    # Инициализация с необязательным task_id
    def __init__(self, task_id: Optional[str] = None):
        self.task_id = task_id

    # Успешный ответ с данными
    def success(self, data: dict) -> dict:
        return {
            "task_id": self.task_id,
            "status": "done",
            "result": data,
            "error": None,
        }
    
    # Ответ с ошибкой и необязательным кодом ошибки
    def error(self, message: str, code: Optional[int] = None) -> dict:
        return {
            "task_id": self.task_id,
            "status": "error",
            "result": {},
            "error": {"message": message, "code": code},
        }
    
    # Успешный ответ с данными
    def success_async(self, data: dict) -> dict:
        return {
            "task_id": self.task_id,
            "status": data['status'],
            "result": data['result'],
            "error": None,
            "created_at": data['created_at'] if 'created_at' in data else None,
            "updated_at": data['updated_at'] if 'updated_at' in data else None
        }
    
    # Ответ с ошибкой и необязательным кодом ошибки
    def error_async(self, message: str, code: Optional[int] = None) -> dict:
        return {
            "task_id": self.task_id,
            "status": "error",
            "result": {},
            "error": {"message": message, "code": code},
        }

    
    
    # Успешный ответ с данными
    def success_fts(self, data, task_data) -> dict:
        return {
            "start": task_data['created_at'],
            "end": task_data['updated_at'],
            "result": [data],
            "error": 'false',
            "error_code": 0,
            "error_msg": '',
        }
    
    # Успешный ответ с данными
    def error_fts(self, message: str, code: Optional[int] = None) -> dict:
        return {
            "result": [],
            "error": 'true',
            "error_code": code,
            "error_msg": message,
        }

    # Вспомогательный метод для преобразования данных в JSON строку
    def json_str(self, payload: dict, ensure_ascii: bool = False) -> str:
        return json.dumps(payload, ensure_ascii=ensure_ascii)