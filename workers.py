from factory.parserFactory import parserFactory
from factory.modelFactory import modelFactory
from utils.taskHelper import taskHelper
from queue import Queue
import threading
import traceback
import json
import schedule
import time
from datetime import datetime, timedelta


# Очереди для каждого парсера
queues = {parser_name: Queue() for parser_name in parserFactory.parsers.keys()}

# Класс для управления рабочими потоками
class Workers:

    # Потоки для обновления токенов и капч
    @staticmethod
    def start_token_threads():
        for parser_name in parserFactory.parsers.keys():
            parser = parserFactory.get_parser(parser_name)
            model = modelFactory.get_model(parser_name)
            thread = threading.Thread(target=parser.thread_worker, daemon=True, name=f"TokenThread{parser_name}", args=(model, ))
            thread.start()


    # Рабочий поток для обработки задач из очереди (асинхронный парсинг)
    @staticmethod
    def queue_worker(parser_name, queue):
        parser = parserFactory.get_parser(parser_name)
        while True:
            try:
                params = queue.get()
                if params is None:
                    continue

                if datetime.now() - params.call_date > timedelta(seconds=10):
                    print(f"Task {params.task_id} has expired.")
                    taskHelper.result_task(params.task_id, result='', error="Task expired")
                    queue.task_done()
                    continue

                result = taskHelper.get_cached_result(params) if params.cache == 1 else None
                if result is None:
                    result = parser.parse(params)
                taskHelper.result_task(params.task_id, result=json.dumps(result, ensure_ascii=False), error=None)
                queue.task_done()

            except Exception as e:
                print(f"Error processing task in {parser_name} parser: {str(e)}")
                taskHelper.result_task(params.task_id, result='', error=str(e))
                traceback.print_exc()
                queue.task_done()

    # Запуск рабочих потоков для каждой очереди парсеров (асинхронный парсинг)
    @staticmethod
    def start_queue_workers():
        for parser_name, queue in queues.items():
            thread = threading.Thread(target=Workers.queue_worker, daemon = True, name=f"QueueConsumer{parser_name}", args=(parser_name, queue))
            thread.start()
            print(f'Started queue worker for {parser_name} parser')

    @staticmethod
    def schedule_workers():
        taskHelper.clear_old_cache()
        schedule.every().day.at("22:00").do(taskHelper.clear_old_cache)
        while True:
            schedule.run_pending()
            time.sleep(10)

    @staticmethod
    def start_scheduler_thread():
        thread = threading.Thread(target=Workers.schedule_workers, daemon=True, name="SchedulerThread")
        thread.start()

    # Получение очереди по имени парсера
    @staticmethod
    def get_queue(parser_name: str) -> Queue:
        queue = queues.get(parser_name)
        if not queue:
            raise ValueError(f"Queue for parser '{parser_name}' not found.")
        return queue