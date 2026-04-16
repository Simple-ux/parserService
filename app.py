import traceback, uuid, json
import uvicorn
import warnings
from http.client import HTTPException
from fastapi import FastAPI, HTTPException, Depends
from schema import SyncRequest, AsyncRequest, AsyncResult, SyncRequestFTS
from factory.parserFactory import parserFactory
from utils.taskHelper import taskHelper
from workers import Workers
from utils.responseBuilder import ResponseBuilder
import asyncio
warnings.filterwarnings('ignore')


# Загрузка моделей
from factory.modelFactory import modelFactory
app = FastAPI(debug=True)

# Основной маршрут для парсинга синхронно
@app.get("/parse/")
async def read_items(params: SyncRequest = Depends()):

    response = ResponseBuilder(task_id=params.task_id)
    try:
        # Логирование задачи, выбор парсера
        taskHelper.create_task(params)
        parser = parserFactory.get_parser(params.parser_type)

        # Берем результат из кэша, если он есть. Если нет, то парсим
        result = taskHelper.get_cached_result(params) if params.cache == 1 else None
        if result is None:
            result = parser.parse(params)

        taskHelper.result_task(params.task_id, result=json.dumps(result, ensure_ascii=False), error=None)
        return response.success(result)

    except ValueError as e:
        taskHelper.result_task(params.task_id, result=None, error=str(e))
        return response.error(str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        taskHelper.result_task(params.task_id, result=None, error=str(e))
        return response.error("Internal Server Error", code=500)
    

# Маршрут для создания задачи на парсинг асинхронно
@app.get("/create_task/")
async def async_create_task(params: AsyncRequest = Depends()):

    #Проверяем наличие кэша в статусе done или processing, если кэш есть, то сразу возвращаем task_id, если нет, то создаем задачу на парсинг

    response = ResponseBuilder(task_id=params.task_id)
    try: 
        #TODO убрать этот костыль и сделать через классы и наследование, чтобы не дублировать код для разных парсеров
        # Если передан VIN, проверяем, есть ли уже активная или готовая задача для него
        if params.vin:
            processing_task_id = taskHelper.get_active_vin_task(params.vin, params.parser_type)
            if processing_task_id:
                return {"task_id": processing_task_id}

        # Выбор очереди парсера и добавление новой задачи в очередь
        queue = Workers.get_queue(params.parser_type)
        taskHelper.create_task(params)
        queue.put(params)
        return {"task_id": params.task_id}
    
    except ValueError as e:
        return response.error(str(e), code=400)
    except:
        traceback.print_exc()
        return response.error("Internal Server Error", code=500)

    
# Получение результата
@app.get("/task_status/{task_id}")
async def async_task_status(params: AsyncResult = Depends()):

    response = ResponseBuilder(task_id=params.task_id)
    try:
        # Получение результата задачи по ID
        result = taskHelper.get_task_status(params.task_id)
        return response.success_async(result)
    
    except ValueError as e:
        return response.error(str(e), code=400)
    except:
        traceback.print_exc()
        return response.error("Internal Server Error", code=500)
    

# Получение результата с ожиданием (пуллинг с таймаутом)
@app.get("/task_status/{task_id}/wait")
async def async_task_wait(params: AsyncResult = Depends(), timeout: int = 20):

    response = ResponseBuilder(task_id=params.task_id)
    interval = 0.1  # Интервал между проверками статуса задачи
    timeout = timeout/interval  # Количество итераций для достижения таймаута
    try:
        # Получение результата задачи по ID
        while timeout > 0:
            result = taskHelper.get_task_status(params.task_id)
            if result["status"] != 'Processing':
                return response.success_async(result)
            await asyncio.sleep(interval)
            timeout -= 1

        if timeout <= 0:
            return response.error("Timeout waiting for task result", code=408)
    
    except ValueError as e:
        return response.error(str(e), code=400)
    except:
        traceback.print_exc()
        return response.error("Internal Server Error", code=500)
    


# Основной маршрут для парсинга синхронно
@app.get("/parseFTS/")
async def read_items_fts(params: SyncRequestFTS = Depends()):

    response = ResponseBuilder(task_id=params.task_id)
    try:
        # Логирование задачи, выбор парсера
        taskHelper.create_task(params)
        parser = parserFactory.get_parser(params.parser_type)

        # Берем результат из кэша, если он есть. Если нет, то парсим
        result = taskHelper.get_cached_result(params) if params.cache == 1 else None
        if result is None:
            result = parser.parse(params)

        taskHelper.result_task(params.task_id, result=json.dumps(result, ensure_ascii=False), error=None)
        task_row = taskHelper.get_task_by_id(params.task_id)
        return response.success_fts(result, task_row)

    except ValueError as e:
        taskHelper.result_task(params.task_id, result=None, error=str(e))
        return response.error_fts(str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        taskHelper.result_task(params.task_id, result=None, error=str(e))
        return response.error_fts("Internal Server Error", code=500)
    
@app.get("/health/")
async def health_check():
    return {"status": "healthy"}

    
# Вспомогательная функция для поднятия HTTP ошибок
def raise_error(params, error, status_code):
    detail = {'parser': params.parser_type, 'error': str(error)}
    raise HTTPException(status_code=status_code, detail=detail)


# Запуск фоновых рабочих потоков при старте приложения
@app.on_event("startup")
async def startup_event():
    # Запуск потоков для обновления токенов и капч
    Workers.start_token_threads()

    # Запуск рабочих потоков для обработки очередей парсеров (асинхронный парсинг)
    Workers.start_queue_workers()

    # Запуск планировщика для очистки кэша
    Workers.start_scheduler_thread()


if __name__ == "__main__":
    uvicorn.run('app:app', log_level="debug", port=10221, workers = 1)
    # os.system('uvicorn app:app --host 0.0.0.0 --port 8080  --workers 1')