import os
import sys
import requests
import csv
import user_agent
import datetime
import json
import random,  time
import traceback
import pandas as pd
import numpy as np
import concurrent.futures
import threading
import queue
import string

from bs4 import BeautifulSoup
from tqdm import tqdm
from requests_toolbelt.multipart.encoder import MultipartEncoder
from parserNSIS.htmlKeys import keys


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from proxy import proxies
from baseParser import BaseParser

class ParserNSIS(BaseParser):
    proxies = proxies

    def get_process_id(session, data):
        try:
            req_queue = session.post('https://nsis.ru/handle-form/1314895756519276544/', data=data, timeout = 60)
            cookies = req_queue.cookies.get_dict()
            if "запросов в час" in req_queue.text or req_queue.status_code == 408:
                return '', 0, {}
            if req_queue.status_code == 104:
                print('blocked')
            answ= json.loads(req_queue.text)
            isSuccess = 1 if answ['isSuccess'] == True else 0
            
            if isSuccess == 1:
                process_id = answ['data']['processId']
            else:
                process_id = ''

            if isSuccess == 1:
                return process_id, isSuccess, cookies
            else:
                return '', 0, {}
        
        except requests.exceptions.ReadTimeout:
                pass
        except Exception as e:
            print(f"ERROR get_process {e}")
            return '', 0 ,{}

    def generate_boundary(len = 16):
        chars = string.ascii_letters + string.digits
        return '----WebKitFormBoundary' + ''.join(random.choices(chars, k=len))


    def parse(params):

        vin = params.vin
        grz = ''
        body_num = ''
        chassi_num = ''
        
        try:
            date = datetime.datetime.now().strftime('%Y-%m-%d')

            # Используем MultipartEncoder для генерации raw тела запроса с boundary.
            # У нсиса хитровыебаная защита через соответствие кол-ва символов в raw теле и content-length. 
            # При этом content-length должен быть в каком-то допустимом промежутке ~от 640 до 680, при иных значениях могут возникать ошибки

            data = MultipartEncoder(
                fields={
                            "vin": vin if vin else "",
                            "requestdate": date,
                            "idExternal": "",
                            "licenseplate": grz if vin == "" else "",
                            "bodynumber": body_num if (vin == "") and (grz == "") else "",
                            "chassisnumber": chassi_num if (vin == "") and (grz == "") and (body_num == "") else ""
                        },
                boundary = ParserNSIS.generate_boundary() 
                        )
            
            headers_queue = {
                            "Referer": "https://nsis.ru/products/osago/check/",
                            "Host": "nsis.ru",
                            "X-Requested-With": "XMLHttpRequest",
                            "Cache-Control": "no-cache",
                            "Cookie": "__admin_identity=9f990967a73c8e5d41c17ea5af9aeadb",
                            "Content-Type": data.content_type,
                            "Content-Length": str(data.len),
                            "User-Agent": user_agent.generate_user_agent()
                        }



            proxies = ParserNSIS.get_proxy()
            session = requests.Session()
            session.proxies = proxies
            headers_queue['User-Agent'] = user_agent.generate_user_agent()
            session.headers.update(headers_queue)
            
            process_id, isSuccess, cookies = ParserNSIS.get_process_id(session,  data)
            
            if isSuccess == 1:
                for cookie in cookies.keys():
                    session.cookies.set(cookie, cookies[cookie], domain = 'nsis.ru')

            
            i = 0
            while isSuccess == 0 and i <= 5:

                session = requests.Session()
                session.proxies = ParserNSIS.get_proxy()
                try:
                    headers_queue['User-Agent'] = user_agent.generate_user_agent()
                    session.headers.update(headers_queue)
                    process_id, isSuccess, cookies = ParserNSIS.get_process_id(session,  data)
                    
                    if isSuccess == 1:
                        for cookie in cookies.keys():
                            session.cookies.set(cookie, cookies[cookie], domain = 'nsis.ru')

                except Exception as e:
                    print(e)
                    
                i += 1


            result_headers={
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Content-Type': 'application/json',
                'Referer': 'https://nsis.ru/products/osago/check/',
                'Host': 'nsis.ru',
                'Pragma': 'no-cache',
                'X-Requested-With': 'XMLHttpRequest',
                'Cache-Control': 'no-cache',
                'Cookie': '__admin_identity=9f990967a73c8e5d41c17ea5af9aeadb'
            }
            time.sleep(3)
            html = ''

            # В цикле проверяем статус отправленной задачи

            status = 'PROCESSING'
            max_attempts = 10
            attempt = 0

            while status == 'PROCESSING':
                if attempt == max_attempts:
                    break
                attempt += 1
                session = requests.Session()
                session.proxies = ParserNSIS.get_proxy()
                headers_queue['User-Agent'] = user_agent.generate_user_agent()
                session.headers.update(result_headers)

                if isSuccess == 1:
                    for cookie in cookies.keys():
                        session.cookies.set(cookie, cookies[cookie], domain = 'nsis.ru')
                try:
                    req_result = session.get(f'https://nsis.ru/api/v1/status/{process_id}/?formCode=check_osago_fact_transport', headers = result_headers, timeout=60)
                except:
                    continue
                
                if "status" not in req_result.text:
                    
                    if "per hour" in req_result.text:
                        print("Changing proxy. Geting result")
                        session.proxies = ParserNSIS.get_proxy()
                        continue
                    if req_result.status_code == 301:
                        print("301")

                    req_result = {'data':{'status': 'ERROR'}}

                else:
                    req_result= json.loads(req_result.text)

                if req_result['data']['status'] == 'PROCESSING' and isSuccess == 1:
                    time.sleep(1)
                    continue
                elif req_result['data']['status'] == 'DONE' and isSuccess == 1:
                    status = 'DONE'
                    html = req_result['modals']['html']
                    time.sleep(2)
                    break

                #Повторная попытка. Иногда процесс в очереди встает в ошибку на стороне нсиса
                elif req_result['data']['status'] == 'ERROR' and isSuccess == 1:
                    session.close()

                    # Заново создаем запрос,  ибо нсис блокирует идентичные запросы
                    data = MultipartEncoder(
                        fields={
                            "vin": vin,
                            "requestdate": date,
                            "idExternal": "",
                            "licenseplate": grz if vin == "" else "",
                            "bodynumber": body_num if (vin == "") and (grz == "") else "",
                            "chassisnumber": chassi_num if (vin == "") and (grz == "") and (body_num == "") else ""
                        },
                            boundary = ParserNSIS.generate_boundary()
                        )
                    headers_queue = {
                            "Referer": "https://nsis.ru/products/osago/check/",
                            "Host": "nsis.ru",
                            "X-Requested-With": "XMLHttpRequest",
                            "Cache-Control": "no-cache",
                            "Cookie": "__admin_identity=e2fa14c746a31d5735cb0a68e2844470",
                            "Content-Type": data.content_type,
                            "Content-Length": str(data.len),
                            "User-Agent": user_agent.generate_user_agent()
                        }
                    time.sleep(1)
                    session = requests.Session()
                    session.proxies = ParserNSIS.get_proxy()
                    session.proxies = proxies
                    headers_queue['User-Agent'] = user_agent.generate_user_agent()
                    session.headers.update(headers_queue)

                    process_id, isSuccess, cookies = ParserNSIS.get_process_id(session,  data)
                    if isSuccess == 1:
                        for cookie in cookies.keys():
                            session.cookies.set(cookie, cookies[cookie], domain = 'nsis.ru')
                        print(f'Success retry - {vin}')
                    continue 
                    
                else:
                    status = 'EXIT ERROR'
                    print(f'ERROR. Exit process. VIN - {vin}', flush = True)
                    break

            data = {}
            found = False
            if html != '':
                soup = BeautifulSoup(html, "html.parser")
                found = True
                # Парсим серию и номер полиса
                
                # Дата
                date_tag = soup.select_one('.tag span')
                if date_tag:
                    data['date'] = date_tag.get_text(strip=True)
                    data['parsed_dog_start_date'] = ''
                    data['parsed_dog_end_date'] = ''
                
                # Парсим все элементы dataList
                for item in soup.select('.dataList__item'):
                    label = item.select_one('.dataList__labelText')
                    value = item.select_one('.dataList__value')
                    

                    if label and value:
                        label_text = label.get_text(strip=True).rstrip(':').lower()
                        data[keys[label_text]] = value.get_text(' ', strip=True)
                        data['veh_vin'] = vin
                        data['veh_reg_number'] = grz
                        data['veh_body_number'] = body_num
                        data['veh_chassis_number'] = chassi_num

            session.close()
            if data == {}:
                data['date'] = '-'
                data['policy_serial'] = '-'
                data['veh_vin'] = vin
                data['veh_reg_number'] = grz

            data['vin'] = vin

            return data
        
        except Exception as e:
            print(str(e))
            traceback.print_exc()


