import os
import sys
import requests
import pandas as pd
import datetime, time
import traceback
import threading
import concurrent.futures
import random
import queue
import sqlite3
import user_agent

from bs4 import BeautifulSoup
from tqdm import tqdm


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from baseParser import BaseParser


class ParserFTS(BaseParser):
    session = ''
    xsrf_token = ''


    #Апдейт xsrf токена в сессии каждые 1-3 минуты
    @classmethod
    def thread_worker(cls, model = None):
        print(f'Started thread for FTS parser')
        while True:
            try:
                session = requests.Session()
                session.proxies = ParserFTS.get_proxy()
                xsrf_token, session = ParserFTS.get_xsrf(session)
                ParserFTS.session = session
                ParserFTS.xsrf_token = xsrf_token
                print('FTS xsrf token has been updated')
                time.sleep(random.randint(320, 600))
            except Exception as e:
                print(f'Error updating FTS xsrf token {e}')


    #Получение xsrf токена с главной страницы
    @staticmethod
    def get_xsrf(session):
        resp_get = session.get('https://customs.gov.ru/', timeout=20)
        cookies = dict(resp_get.cookies.get_dict())
        for cookie in cookies.keys():
            session.cookies.set(cookie, cookies[cookie], domain = f'customs.gov.ru')

        soup = BeautifulSoup(resp_get.text, 'html.parser')
        

        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            raise Exception("Не удалось найти _token")

        xsrf_token = token_input['value']
        return xsrf_token, session


    @staticmethod
    def parse(params):

        try:

            if params.vin:
                vin = params.vin
            else:
                vin = None
                raise ValueError("VIN номер не указан")
            
            session = ParserFTS.session
            headers = {
                'User-Agent': user_agent.generate_user_agent(),
                'Referer': 'https://customs.gov.ru/cars'
            }

            session.headers.update(headers)
            
            payload = {
                '_token': ParserFTS.xsrf_token,
                'vin': vin
            }
            start = datetime.datetime.now()
            resp_post = session.post('https://customs.gov.ru/cars', data=payload, timeout=20)
            print(datetime.datetime.now() - start)
            soup = BeautifulSoup(resp_post.text, 'html.parser')

            

            data = {
                'Vin': vin,
                'BodyNumber': 'null',
                'ChassisNumber': 'null',
                'ReleaseDate': 'null',
                'CountryShort': 'null',
                'MarkaModel': 'null',
                'FindStatus': 0
            }

            keys = {
                'номер vin': 'Vin',
                'модель': 'MarkaModel',
                'номер кузова': 'BodyNumber',
                'номер шасси': 'ChassisNumber',
                'дата выпуска в свободное обращение': 'ReleaseDate'
            }
            for item in soup.select('.vin-check__card-item'):
                title = item.select_one('.vin-check__card-title')
                value = item.select_one('.vin-check__card-info')
                if title and value:
                    key = title.get_text(strip=True).lower()
                    val = value.get_text(strip=True)
                    if key in keys:
                        data[keys[key]] = val

            flag_img = soup.select_one('.vin-check__card-img img[src*="flags/"]')
            if flag_img:
                src = flag_img['src']
                country_code = src.split('/')[-1].replace('.svg', '')
                data['CountryShort'] = country_code.upper()

            if data['BodyNumber'] != 'null' and data['ChassisNumber'] != 'null':
                data['FindStatus'] = 1

            fmt = "%Y-%m-%d"
            formated_date = data['ReleaseDate'].split(' ')[0]
            if formated_date != 'null':
                formated_date = datetime.datetime.strptime(str(formated_date), fmt).date()
                formated_date = formated_date.strftime("%d.%m.%Y")
            data['ReleaseDate'] = formated_date

            session.close()
            return data

        except Exception as e:
            print(f"[FTS ERROR] {vin} - {str(e)}")
            traceback.print_exc()
            raise ValueError(e)