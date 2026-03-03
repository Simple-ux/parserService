import os
import pandas as pd
import os, sys, queue, random
import datetime, time
import urllib3, requests
from user_agent import generate_user_agent
import json
from bs4 import BeautifulSoup
from pydub import AudioSegment
import re
import base64
from io import BytesIO
import tensorflow as tf
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



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
        try:
            status_code = 0
            while status_code != 200:
                req = session.get(f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={middle_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}', verify= False)
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
                req = session.get(link, verify= False, timeout = 10)
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

        parsed = parsed.to_dict(orient="records")
        result = {}
        result['last_name'] = last_name
        result['first_name'] = name
        result['middle_name'] = middle_name
        result['birth_date'] = birthdate
        result['data'] = parsed

        return result