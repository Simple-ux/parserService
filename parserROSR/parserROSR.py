import base64
import os
import sys
from urllib import response
from wsgiref import headers
import requests
import user_agent
import datetime
import json
import random,  time
import traceback
import pandas as pd
import numpy as np
import httpx
from PIL import Image
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pathlib import Path
from urllib.parse import quote



parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from parserROSR import mapParams
from parserROSR.preprocess import Preprocess
from parserROSR.predict import predict_captcha
from proxy import proxies
from baseParser import BaseParser


class ParserROSR(BaseParser):


    def captcha(enc):
            api_key = '776135b9c29c1b633b9d408cef0882df'
            data = {
                "clientKey": api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": enc,
                    "phrase": False,
                    "case": False,
                    "numeric": 0,
                    "math": False,
                    "minLength": 5,
                    "maxLength": 5,
                    "comment": "введите текст, который вы видите на изображении"
                },
                "softId": "3898",
                "languagePool": "en"
            }

            try:
                req = requests.post('https://api.rucaptcha.com/createTask', json=data)
                task = json.loads(req.text)
            except Exception as e:
                print('captcha', e)
                return
            task_id = task['taskId']
            
            data = {
                "clientKey": api_key, 
                "taskId": task_id
            }
            i = 0
            while True and i < 15:
                try:
                    req = requests.post('https://api.rucaptcha.com/getTaskResult', json=data)
                    task = json.loads(req.text)
                    if task['status'] == 'processing':
                        print('processing')
                        time.sleep(2)
                        i += 1
                        continue
                    elif task['status'] == 'ready':
                        return task['solution']

                    else:
                        print('error')
                        break
                except:
                    return

    
    def solve_captcha(session):
        try:
            captcha_req = session.get('https://lk.rosreestr.ru/account-back/captcha.png', timeout = httpx.Timeout(5.0, connect=5.0))
            img_content = captcha_req.content

            cookie_string = "; ".join(
                    f"{cookie.name}={cookie.value}"
                    for cookie in session.cookies.jar
                )

            encoded_bytes = base64.b64encode(captcha_req.content)
            encoded_string = encoded_bytes.decode('utf-8')

            if captcha_req.status_code == 200:
                
                # solved = ParserRosreestr.captcha(encoded_string)
                solved = predict_captcha(captcha_req.content)
                print(solved)
                if not solved:
                    return None, session, None
                return solved, session, img_content

        except Exception as e:
            print(f"ERROR solve_captcha {e}")
            return None, session, None
        

    def get_data(session, cad_number, solved_captcha):
        try:
            body = {"filterType":"cadastral",
                    "cadNumbers":[cad_number],
                    "captcha":solved_captcha}
            
            

            captcha_req = session.post('https://lk.rosreestr.ru/account-back/on', json=body, timeout = httpx.Timeout(5.0, connect=5.0))
            dict_data = json.loads(captcha_req.text)
            return dict_data

        except Exception as e:
            print(f"ERROR get_data {e}")
            return None 
        

    def find_cad(address, session):
        try:
            address = address.strip().replace(' ', '+')
            params = {'term': address, "objType": "002001003000"}
            response = session.get('https://lk.rosreestr.ru/account-back/address/search', params=params, timeout = httpx.Timeout(5.0, connect=5.0))
            data = json.loads(response.text)
            if data != [] and len(data) <= 3:
                cadnum = data[0].get('cadnum')
                address = data[0].get('full_name')
                type = data[0].get('flat')
                return cadnum, address, type
            else:
                return None, None, None
        except Exception as e:
            print(f"ERROR find_cad {e}")
            return None,None,None

    def parse(params):
        try:
            address = params.addr
            cadnum = params.cad

            if not address and not cadnum:
                raise ValueError("Не указан адрес и кадастровый номер")

            start = datetime.datetime.now()
            date = datetime.datetime.now().strftime('%Y-%m-%d')
            proxies = ParserROSR.get_proxy(format="httpx")
            user_agent_str = user_agent.generate_user_agent()
            captcha_headers = {
                "content-type": "image/png;charset=UTF-8",
                "Host": "lk.rosreestr.ru",
                "User-Agent": user_agent_str,
                "Accept": "image/png,*/*",
                "Referer": "https://lk.rosreestr.ru/",
            }

            # session.headers.update(captcha_headers)

            for i in range(5):
                session = httpx.Client(
                    headers=captcha_headers,
                    proxies=proxies,
                    verify=False
                    )           
                
                solved_captcha = None

                solved_captcha, session, img_content= ParserROSR.solve_captcha(session)
                if solved_captcha:
                    break
                else:
                    session.close()


            session.headers = httpx.Headers({
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "Host": "lk.rosreestr.ru",
                "User-Agent": user_agent_str,
                "Origin": "https://lk.rosreestr.ru",
            })

            if cadnum is None:
                cadnum, pretty_address, type = ParserROSR.find_cad(address, session)
            else:
                pretty_address = None
                type = None

            
            if cadnum:
                data = ParserROSR.get_data(session, cad_number=cadnum, solved_captcha=solved_captcha)
                
                session.close()
                solved_key = 0
                if 'elements' in data.keys():
                    solved_key = 1
                else:
                    print(f'Wrong captcha for {address}')
                    return
                
                elements = data.get('elements')[0]
                data = mapParams.structure_keys()
                for key in elements.keys():
                    data[key] = elements.get(key)

                
                data['cadnum'] = cadnum
                data['address'] = address
                data['pretty_address'] = elements['address']['readableAddress'] if elements['address'] else None
                data['type'] = type
                data['status'] = 'Актуально' if data['status'] == '1' else data['status']
                data['objType'] = mapParams.object_type(data['objType'])
                data['regDate'] = datetime.datetime.fromtimestamp(data['regDate'] / 1000).strftime('%Y-%m-%d') if data.get('regDate') else None
                data['cadCostDeterminationDate'] = datetime.datetime.fromtimestamp(data['cadCostDeterminationDate'] / 1000).strftime('%Y-%m-%d') if data.get('cadCostDeterminationDate') else None
                data['cadCostRegistrationDate'] = datetime.datetime.fromtimestamp(data['cadCostRegistrationDate'] / 1000).strftime('%Y-%m-%d') if data.get('cadCostRegistrationDate') else None
                data["infoUpdateDate"] = datetime.datetime.fromtimestamp(data['infoUpdateDate'] / 1000).strftime('%Y-%m-%d') if data.get('infoUpdateDate') else None
                data['find_status'] = 1

            else:
                data = mapParams.structure_keys()
                data['cadnum'] = 'Не найдено'
                data['pretty_address'] = None
                data['type'] = None
                data['address'] = address
                data['find_status'] = 0
            
            return data
        
        except Exception as e:
            traceback.print_exc()
            raise ValueError(e)
