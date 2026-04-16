import sqlite3
import datetime
import traceback
import json

class taskHelper:

    # Создание новой задачи в базе данных
    @classmethod
    def create_task(cls, params):
        conn = sqlite3.connect('tasks.db')
        call_date = cls.get_datetime_now()
        try:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO tasks (id, call_type, service, vin, status, result, error, created_at, updated_at) 
                            VALUES (?,?, ?, ?, ?, ?, ?, ?, ?)""",
                        (params.task_id, params.call_type, params.parser_type, params.vin, 'Processing', '', '', call_date, '',))
            conn.commit()
        except Exception as e:
            traceback.print_exc()
        finally:
            conn.close()
        return 
    
    # Обновление результата задачи в базе данных
    @classmethod
    def result_task(cls, task_id: str, result: str = '', error: str = ''):
        conn = sqlite3.connect('tasks.db')
        result_date = cls.get_datetime_now()
        status = 'Done' if not error else 'Error'
        try:
            cursor = conn.cursor()
            cursor.execute("""  UPDATE tasks 
                                SET status = ?, result = ?, error = ?, updated_at = ? 
                                WHERE id = ?""",
                            (status, result, error, result_date, task_id,))
            conn.commit()
        except Exception as e:
            traceback.print_exc()
        finally:
            conn.close()
        return
    
    # Получение результата задачи из базы данных
    @classmethod
    def get_task_status(cls, task_id: str):
        conn = sqlite3.connect('tasks.db')
        try:
            cursor = conn.cursor()
            cursor.execute(""" SELECT status, result, error, created_at, updated_at
                                FROM tasks 
                                WHERE id = ?""",
                            (task_id,))
            row = cursor.fetchone()


            if row:
                status, result, error, created_at, updated_at = row
                created_at = created_at if created_at else None
                updated_at = updated_at if updated_at else None

                if status == 'Error':
                    raise ValueError(error)
                else:
                    result = json.loads(result) if result else {}
            else:
                raise ValueError("Task ID not found")
            
            return {
                "result": result,
                "created_at": created_at,
                "updated_at": updated_at,
                'status': status
            }
        
        except Exception as e:
            traceback.print_exc()
            raise e
        finally:
            conn.close()

    # Получение кэшированного результата по VIN и типу парсера
    @classmethod
    def get_cached_result(cls, params):
        conn = sqlite3.connect('tasks.db')
        try:
            cursor = conn.cursor()
            cursor.execute(""" SELECT result from tasks 
                                WHERE vin = ? AND service = ? AND status = 'Done'""",
                            (params.vin, params.parser_type,))
            row = cursor.fetchone()
        except Exception as e:
            traceback.print_exc()
            raise e
        finally:
            conn.close()

        if row:
            result = row[0]
            result = json.loads(result) if result else None
            return result
        
    @classmethod
    def clear_old_cache(cls):
        conn = sqlite3.connect('tasks.db')
        try:
            cursor = conn.cursor()
            cursor.execute(""" DELETE FROM tasks WHERE created_at < date('now', '-5 days')""")
            conn.commit()
        except Exception as e:
            traceback.print_exc()
        finally:
            conn.close()
        return
    
    @classmethod
    def get_task_by_id(cls, task_id: str):
        conn = sqlite3.connect('tasks.db')
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(""" SELECT *
                                FROM tasks 
                                WHERE id = ?""",
                            (task_id,))
            row_dict = dict(cursor.fetchone())

            return row_dict
        except Exception as e:
            traceback.print_exc()
        finally:
            conn.close()

    # Получение активной (Processing или Done) задачи по VIN и типу парсера
    @classmethod
    def get_active_vin_task(cls, vin: str, parser_type: str):
        conn = sqlite3.connect('tasks.db')
        try:
            cursor = conn.cursor()
            cursor.execute(""" SELECT id, status from tasks 
                                WHERE vin = ? AND service = ? AND status = 'Processing'
                                ORDER BY created_at DESC LIMIT 1""",
                            (vin, parser_type,))
            row = cursor.fetchone()
        except Exception as e:
            traceback.print_exc()
            raise e
        finally:
            conn.close()

        if row:
            return row[0]
        return None
    
    # Вспомогательная функция для получения текущей даты и времени в нужном формате
    @classmethod
    def get_datetime_now(cls):
        call_date = datetime.datetime.now()
        call_date = call_date.strftime('%Y.%m.%d %H:%M:%S.%f')[:-3]
        return call_date
    