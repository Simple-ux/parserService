import os
import soundfile as sf
import numpy as np
import pandas as pd
import concurrent.futures
import os, sys, queue, random
import datetime, time
import urllib3, requests
import threading
from user_agent import generate_user_agent
import json
from bs4 import BeautifulSoup
from pydub import AudioSegment
import re
import base64
from io import BytesIO
from tqdm import tqdm
from predict import predict, predict_tflite
import tensorflow as tf
import warnings
warnings.filterwarnings('ignore')

lock = threading.Lock()

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from proxy import proxies as pr

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

q = queue.Queue()
node_q = queue.Queue()
tasks = queue.Queue()

model = tf.keras.models.load_model("parserFSSP/captcha_model.keras")


class parserFSSP():

    

    def get_proxy(put = 1):
        proxy = q.get_nowait()
        proxy_splited = proxy.split(':')

        proxy_user = proxy_splited[2]
        proxy_pass = proxy_splited[3]
        proxy_host = proxy_splited[0] + ':' + proxy_splited[1]

        proxies= {  "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}",
                    "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}"}
        
        if put == 1:
            q.put(str(proxy))
        
        return proxies
    


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


    def parse(last_name, name, father_name, birthdate, result_file, index):
        
        start = datetime.datetime.now()

        headers = {}
        headers['User-Agent'] = generate_user_agent()
        headers['Host'] = f'is-go.fssp.gov.ru'
        headers['Referer'] = 'https://fssp.gov.ru/'
        headers['accept-encoding'] = 'gzip, deflate, br, zstd'


        session = requests.Session()        
        proxies = parserFSSP.get_proxy()
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
                req = session.get(f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={father_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}', verify= False)
                if req.status_code != 200:
                    print('NODE ERROR ', req.status_code)
                    print(req.text)
                    proxies = parserFSSP.get_proxy()
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
        solved = predict_tflite(audio_data)

        if not solved:
            print('NOT SOLVED NULL')
            return
        
        


        # # 2-й запрос, отправляем код, получаем ответ
        answ = 0
        attempt = 0
        while answ == 0 and attempt < 5:          
            timestamp = str(int(time.time() * 1000))

            try:
                link = f'https://is-go.fssp.gov.ru/ajax_search?system=ip&is[extended]=1&nocache=1&is[variant]=1&is[region_id][0]=-1&is[last_name]={last_name}&is[first_name]={name}&is[drtr_name]=&is[ip_number]=&is[patronymic]={father_name}&is[date]={birthdate}&is[address]=&is[id_number]=&is[id_type][0]=&is[id_issuer]=&is[inn]=&callback={callback}&code_id={code_id}&code={solved}&_={timestamp}'
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
            
            parsed = parserFSSP.parse_fssp_data(req.text)
            if parsed.shape[0] == 0:
                print(f'Нет результата по ФИО {name, last_name}')
                return
            
            req_txt = req.text.split('{')
            req_txt = req_txt[1].split('{')[0]

            
            if 'Должник' not in req_txt:
                print(f'retry {solved} - {req_txt}')
                break
            
            answ = 1
            print(f'write {name, last_name} - ', index)

        file_exists = os.path.isfile(result_file)

        parsed['LASTNAME'] = last_name
        parsed['FIRSTNAME'] = name
        parsed['MIDDLENAME'] = father_name
        parsed['INSURER_BIRTH_DATE'] = birthdate

        print(parsed)
        with lock:
            mode = 'a' if file_exists else 'w'
            headers = True if mode == 'w' else False
            parsed.to_csv(result_file, mode = mode, header = headers, encoding='cp1251', sep=';', index=False)

        # print(datetime.datetime.now() - start)  




    def worker():
            while True:
                try:
                    last_name, first_name, middle_name, birthdate, result_file, index = tasks.get(timeout=3)
                except queue.Empty:
                    break

                try:
                    parserFSSP.parse(last_name, first_name, middle_name, birthdate, result_file, index)
                except Exception as e:
                    print(e)
                finally:
                    tasks.task_done()



    def is_valid_birthdate(date_str: str, date_format: str = None) -> bool:
        """
        Проверяет валидность даты рождения.
        
        :param date_str: Строка с датой рождения
        :param date_format: Необязательный формат даты. Если не указан, будет пробоваться автодетект.
        :return: True, если дата валидна, иначе False
        """
        if not isinstance(date_str, str):
            return False

        # Возможные форматы, если формат явно не задан
        possible_formats = [
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y.%m.%d",
        ]

        formats_to_try = [date_format] if date_format else possible_formats

        for fmt in formats_to_try:
            try:
                birth_date = datetime.datetime.strptime(date_str, fmt)
                today = datetime.datetime.today()

                # Проверка на будущее
                if birth_date > today:
                    return False

                # Проверка возраста (0–120 лет)
                age = (today - birth_date).days // 365
                if 0 < age <= 120:
                    return True
            except ValueError:
                continue

        return False
    
    def validate_full_name_parts(last_name: str, first_name: str, middle_name) -> bool:
        """
        Проверяет валидность ФИО.
        Допускает, что отчество может отсутствовать
        
        :param last_name: Строка с фамилией
        :param first_name: Строка с именем
        :middle_name: Строка с отчеством
        :return: True, если ФИО валидно, иначе False
        """
        if not all(isinstance(x, str) for x in [last_name, first_name]):
            return False
        if pd.isna(middle_name):  
            middle_name = None
        elif not isinstance(middle_name, str):
            return False

        name_regex = r'^[А-ЯЁа-яё\-]+$'
        for part in [last_name, first_name, middle_name]:
            if part and not re.fullmatch(name_regex, part.strip()):
                return False

        return True


    def start_FSSP(file_path):
        init_file_name = file_path.split('/')[-1].split('.')[0]
        data = pd.read_csv(file_path, encoding="cp1251", sep = ';').drop_duplicates().reset_index(drop=True)
        data.fillna('',inplace=True)
        print('...CSV READ COMPLETED...')
        print('...STARTING...')
        print(init_file_name)

        parse_date = datetime.datetime.now().strftime('%Y-%m-%d')
        result_file = f'{parent_dir}/result_csv/{init_file_name}_FSSP.csv'
        file_exists = os.path.isfile(result_file)



        #Логика случай если парсинг в процессе встал и нужен перезапуск. Чтобы продолжить с последнего вина
        if file_exists:
            parsed_data = pd.read_csv(result_file, encoding="cp1251", sep = ';').fillna('-')
            last_str = parsed_data.iloc[parsed_data.shape[0] - 1]
            data_last_str = data.loc[(data['LASTNAME'] == last_str['LASTNAME']) & (data['FIRSTNAME'] == last_str['FIRSTNAME']) & (data['MIDDLENAME'] == last_str['MIDDLENAME']) & (data['INSURER_BIRTH_DATE'] == last_str['INSURER_BIRTH_DATE'])]
            max_index = data_last_str.index.max()
            data = data[data.index > max_index]
        
        random.shuffle(pr)
        for proxy in pr:
            q.put(proxy)

        nodes = list(range(1,7))
        random.shuffle(nodes)
        for node in nodes:
            node_q.put(str(node))

        data['index'] = data.index
        data = data.to_dict(orient='records')
        for row in tqdm(data):
            tasks.put((row['LASTNAME'], row['FIRSTNAME'], row['MIDDLENAME'], row['INSURER_BIRTH_DATE'], result_file, row['index']))

        threads = []

        for i in range(1):
                thr = threading.Thread(target=parserFSSP.worker)
                thr.start()
                threads.append(thr)
                time.sleep(1)


        for thr in threads:
            thr.join()

# parserFSSP.start_FSSP(sys.argv[1])
parserFSSP.start_FSSP('init_csv/FSSP.csv')