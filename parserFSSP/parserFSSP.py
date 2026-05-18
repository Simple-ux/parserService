import os
import pandas as pd
import os, sys, queue, random
import datetime, time
import urllib3
from user_agent import generate_user_agent
import json
from bs4 import BeautifulSoup
from pydub import AudioSegment
import re
import base64
from io import BytesIO
import tensorflow as tf
from curl_cffi import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from parserFSSP.map_result import HEADER_MAP
from random import shuffle



parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)


from baseParser import BaseParser
from factory.modelFactory import modelFactory
from parserFSSP.predict import predict, predict_tflite


class ParserFSSP(BaseParser):

    model = modelFactory.get_model('FSSP')
    
    def parse_fssp_data(json_response):
        # Извлекаем JSON данные из строки ответа
        # json_str = json_response.replace('\\', '').replace('rn', '').replace('  ', ' ')
        json_str = json_response.split('(', 1)[1].rsplit(')', 1)[0]
        data = json.loads(json_str)
        
        # Парсим HTML таблицу
        soup = BeautifulSoup(data['data'], 'html.parser')
        table = soup.find('table', {'class': 'list'})

        if not table or 'ничего не найдено' in soup:
            df = pd.DataFrame()
            return df
        
        # Собираем заголовки
        headers = []
        for th in table.find('tr').find_all('th'):
            header = th.get_text(' ', strip=True)  # заменяем переносы на пробелы
            headers.append(header)
        
        # Собираем данные из строк
        rows = []
        for tr in table.find_all('tr')[1:]:  # пропускаем заголовок
            if 'region-title' in tr.get('class', []):  # пропускаем строки с регионами
                continue
                
            row = []
            for td in tr.find_all('td'):
                # Извлекаем ВЕСЬ текст, включая содержимое после <br>
                text = ' '.join(td.stripped_strings).replace('\n', ', ').replace('  ', '').replace(', ,', '')  # объединяет все строки через пробел
                row.append(text)
                
            while len(row) < len(headers):
                row.append('')
            rows.append(row)
        
        # Создаём DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        return df


    def parse(params):

        name, last_name, middle_name, birthdate = params.name, params.last_name, params.middle_name, params.birthdate

        headers = {}
        headers['User-Agent'] = generate_user_agent()
        headers['Host'] = f'is-go.fssp.gov.ru'
        headers['Referer'] = 'https://fssp.gov.ru/'
        headers['accept-encoding'] = 'gzip, deflate, br, zstd'


        session = requests.Session()        
        proxies = ParserFSSP.get_proxy()
        session.proxies = proxies
        session.headers.update(headers)



        timestamp = str(int(time.time() * 1000)-5)
        random_number = str(random.randint(10 ** 22, 10 ** 23 - 5000))
        callback = f'jQuery{random_number}_{timestamp}'


        ####################################################
        ####################################################
        # 1-й запрос, получаем капчу

        # ФССП требует HTTP/2, и их антидудос проверяет fingerprint браузера
        # Когда на запрос ниже начинает приходить "Доступ запрещен" - 
        # значит их система срисовала fingerprint и нужно поменять версию браузера в impersonate 
        
        # Возможные версии
        # chrome99
        # chrome100
        # chrome101
        # chrome104
        # chrome107
        # chrome110
        # chrome116 1
        # chrome119 1
        # chrome120 1
        # chrome99_android
        # edge99
        # edge101
        # safari15_3 2
        # safari15_5 2
        # safari17_0 1
        # safari17_2_ios 1


        try:
            status_code = 0
            while status_code != 200:
                # req = session.get(f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={middle_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}', verify= False)
                
                #Рабочие версии браузеров для парсинга ФССП (Пока что)
                BROWSER_VERSIONS = [
                        "chrome99",
                        "chrome100",
                        "chrome101",
                        "chrome104",
                        "chrome107",
                        "chrome110",
                        "chrome116",
                        "safari153",
                        "safari155",
                        "safari170",
                        "safari180",
                        "safari184",
                        "safari260",
                        "safari2601",
                        "firefox133",
                        "firefox135",
                        "firefox144",
                        "firefox147",
                        "tor145"]     

                shuffle(BROWSER_VERSIONS)
                for version in BROWSER_VERSIONS:
                    session = requests.Session(
                        impersonate=version,
                        http_version="v2"
                    )
                    req = session.get(
                        url=f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={middle_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}',
                    )
                    if req.status_code == 200:
                        print(f'Успешно получили капчу с версией {version}')
                        break
                    if req.status_code == 403:
                        print(f'Версия {version} заблокирована, пробуем другую...')
                        continue

                if req.status_code != 200:
                    print('NODE ERROR ', req.status_code)
                    print(req.text)
                    proxies = ParserFSSP.get_proxy()
                    session.proxies = proxies
                    time.sleep(1)
                else:
                    status_code = 200
                
            
        except Exception as e:
            print('1-st err ', e, session.proxies)
            return
        
        req_txt = req.text.replace('\\u0026#43;', '+').replace('\\', '').split('"')
        # ищем капчу в ответе
        
        for i in req_txt:
            if 'data:audio' in i:
                base_audio = i
                break

        for i in req_txt:
            if 'code_id' in i:
                code_id = i
                match = re.search(r'code_id=([^&]+)', code_id)
                if match:
                    code_id = match.group(1)
                break

        # куки
        cookies = dict(req.cookies.get_dict())
        for cookie in cookies.keys():
            session.cookies.set(cookie, cookies[cookie], domain = f'is-go.fssp.gov.ru')

        

        audio_captcha_url_base_64 = base_audio.split(",")[1]
        audio_data = BytesIO(base64.b64decode(audio_captcha_url_base_64))
        audio = AudioSegment.from_file(audio_data)
        start_trim = 1500 
        end_trim = 1000

        # Отрезаем мусор. 1,5 сек. в начале и 1 сек. в конце
        trimmed_audio = audio[start_trim:-end_trim]
        audio_data = BytesIO()
        trimmed_audio.export(audio_data, format="wav")  # или "mp3" и др.
        audio_data.seek(0)
        audio_data = audio_data.getvalue()
        #TODO 
        # solved = predict(audio_data, model)
        solved = predict_tflite(audio_data, ParserFSSP.model)

        if not solved:
            print('NOT SOLVED NULL')
            return
        
        


        # # 2-й запрос, отправляем код, получаем ответ
        answ = 0
        attempt = 0
        while answ == 0 and attempt < 5:          
            timestamp = str(int(time.time() * 1000))

            try:
                link = f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={middle_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}&code_id={code_id}&code={solved}&_={timestamp}'
                req = session.get(link, timeout = 10)
                attempt += 1
                if 'неверных попыток' in req.text:
                    continue
            except Exception as e:
                print(f'retry {solved} - {e}')
                continue
            
            if req.status_code != 200:
                print(f'retry {solved} - {req.status_code}')
                continue
            
            parsed = ParserFSSP.parse_fssp_data(req.text)
            if parsed.shape[0] == 0:
                print(f'Нет результата по ФИО {name, last_name}')
                return
            
            req_txt = req.text.split('{')
            req_txt = req_txt[1].split('{')[0]

            
            if 'Должник' not in req_txt:
                print(f'retry {solved} - {req_txt}')
                break
            
            answ = 1
        try:
            records = parsed.to_dict(orient="records")
            # Map verbose headers to normalized keys
            for rec in records:
                mapped = {}
                for k, v in rec.items():
                    new_key = HEADER_MAP.get(k, k)
                    mapped[new_key] = v
        except Exception as e:
            print(req.text)

        result = {}
        result['last_name'] = last_name
        result['first_name'] = name
        result['middle_name'] = middle_name
        result['birth_date'] = birthdate
        result = {**result, **mapped}

        return result