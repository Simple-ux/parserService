from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, field_validator, ValidationError
import uuid


class SyncRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True) 

    #Параметры
    parser_type: str = Field(..., description="Тип парсера")
    vin: Optional[str] = Field(None, min_length = 12, max_length = 17, description="ВИН номер автомобиля")
    name: Optional[str] = Field(None, max_length = 20, description="Имя")
    last_name: Optional[str] = Field(None, max_length = 20, description="Фамилия")
    middle_name: Optional[str] = Field(None, max_length = 30, description="Отчество")
    birthdate: Optional[str] = Field(None, description="Дата рождения")
    addr: Optional[str] = Field(None, max_length = 300, description="Адрес")
    cad: Optional[str] = Field(None, max_length = 40, description="Кадастровый номер")
    vessel_num: Optional[int] = Field(None, description="Номер судна")
    cache: Optional[int] = Field(1, description="Использовать кэш")

    _call_type: str = PrivateAttr('sync')
    _task_id: str = PrivateAttr(default_factory=lambda: str(uuid.uuid4()))
    _call_date: str = PrivateAttr(default_factory=lambda: datetime.now())

    @property
    def task_id(self):
        return self._task_id
    
    @property
    def call_date(self):
        return self._call_date

    @property
    def call_type(self):
        return self._call_type

    # Валидатор для форматирования даты рождения
    @field_validator("birthdate", mode="before")
    def format_date(cls, date):
        if date:
            formats = [
                "%d.%m.%Y",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%d %b %Y",
                "%d %B %Y",
            ]

            formated_date = None
            for fmt in formats:
                try:
                    formated_date = datetime.strptime(str(date), fmt).date()
                    formated_date = formated_date.strftime("%d.%m.%Y")
                    return formated_date
                except:
                    pass

            if not formated_date:
                print("Invalid date format")
        else:
            pass

    

# Расширение SyncRequest для асинхронных запросов
class AsyncRequest(SyncRequest):
    _call_type: str = PrivateAttr('async')

# Модель для получения результата задачи
class AsyncResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True) 
    task_id: str = Field(None, description="ID задачи")

class SyncRequestFTS(SyncRequest):
    parser_type: str = Field("FTS", description="Тип парсера")


