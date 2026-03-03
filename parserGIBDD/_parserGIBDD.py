import requests
import json
import base64
from io import BytesIO
import cv2
import numpy as np
import concurrent.futures
import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers, models, backend as K
import traceback, random
from PIL import Image
from urllib.parse import urlencode
import user_agent
import datetime, queue, sys, os, threading, json
import time
from tqdm import tqdm


lock = threading.Lock()

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
from proxy import proxies as pr


model = keras.models.load_model("prediction_model_80.keras", compile=False)
q = queue.Queue()
tasks = queue.Queue()


class ParserGIBDD():

    success = 0
    calls = 0
    captcha = {}
    proxies = ''

    @staticmethod
    def decode_predictions(pred, beam_width=5):
        decoded, _ = K.ctc_decode(pred, input_length=np.ones(pred.shape[0]) * pred.shape[1], greedy=True)
        out = K.get_value(decoded[0])
        results = []
        for seq in out:
            results.append(''.join([str(ch) for ch in seq if ch != -1]))
        return results
    
    @staticmethod
    def get_proxy():
        proxy = q.get_nowait()
        proxy_splited = proxy.split(':')

        proxy_user = proxy_splited[2]
        proxy_pass = proxy_splited[3]
        proxy_host = proxy_splited[0] + ':' + proxy_splited[1]

        proxies= {  "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}",
                    "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}"}
        
        q.put(str(proxy))
        
        return proxies
    


    #Капча привязана к каким-то атрибутам сессии, поэтому после решения капчи сессию нужно передавать в функции для парсинга
    def predict(self, session):

        token = ''
        prediction = ''
        headers = { "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Host": "check.gibdd.ru",
                    "Origin": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai",
                    "Pragma": "no-cache",
                    "Referer": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "Sec-Fetch-Storage-Access": "active",
                    "User-Agent": user_agent.generate_user_agent(),
                    "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "Windows"}
        

        # while token == '':
        try:
            session.headers.clear()
            session.headers.update(headers)

            req = session.get('https://check.gibdd.ru/captcha', timeout=3)
            req = json.loads(req.text)
            

            token = req['token']

            img_data = BytesIO(base64.b64decode(req['base64jpg']))
            img = np.frombuffer(img_data.getvalue(), dtype=np.uint8)
            img = cv2.imdecode(img, cv2.IMREAD_COLOR)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
            img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel, iterations=1)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.GaussianBlur(img, (3, 3), 0)

            img = cv2.adaptiveThreshold(
                img, 255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY_INV, 15, 8
            )

            contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            mask = np.zeros_like(img)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 50:
                    cv2.drawContours(mask, [cnt], -1, 255, -1)


            img = cv2.bitwise_and(img, mask)
            _, img_encoded = cv2.imencode('.jpg', img)
            img = Image.open(BytesIO(img_encoded)).convert("L").resize((150, 80))
            img = np.array(img).astype(np.float32) / 255.0
            img = np.expand_dims(img, axis=(0, -1))
            

            prediction = model.predict(img)
            prediction = ParserGIBDD.decode_predictions(prediction)
            

    
        except Exception as e:
            print(e)
            return 0, 0

        self.token = token
        self.prediction = prediction[0]
        
        return token, prediction[0]

    
    @staticmethod
    def reg_data(vin, token, prediction, session, headers):
        try:
            data = {
                "vin": vin,
                "checkType": "history",
                "captchaWord": prediction,
                "captchaToken": token   
            }
            encoded_data = urlencode(data, encoding='UTF-8')
            content_length = str(len(encoded_data.encode('utf-8')))
            headers['content-length'] = content_length
            session.headers.update(headers)


            req = session.post('https://xn--b1afk4ade.xn--90adear.xn--p1ai/proxy/check/auto/register', data = encoded_data, timeout = 60)

            data = json.loads(req.text)

            return data
        except Exception as e:
            print(e, vin)
            if 'timeout' in str(e):
                data['code'] = 408
                return data

    @staticmethod
    def dtp_data(vin, token, prediction, session, headers):
        try:
        # Запрос по дтп
            data = {
                "vin": vin,
                "checkType": "aiusdtp",
                "captchaWord": prediction,
                "captchaToken": token   
            }

            encoded_data = urlencode(data, encoding='UTF-8')
            content_length = str(len(encoded_data.encode('utf-8')))
            headers['content-length'] = content_length
            session.headers.update(headers)
            req = session.post('https://xn--b1afk4ade.xn--90adear.xn--p1ai/proxy/check/auto/dtp', data = encoded_data, timeout = 60)
            data = json.loads(req.text)

            return data
    
        except Exception as e:
            print(e, vin)
            if 'timeout' in str(e):
                data['code'] = 408
                return data


    @staticmethod
    def limits_data(vin, token, prediction, session, headers):
        try:
        # Запрос по дтп
            data = {
                "vin": vin,
                "checkType": "restricted",
                "captchaWord": prediction,
                "captchaToken": token   
            }

            encoded_data = urlencode(data, encoding='UTF-8')
            content_length = str(len(encoded_data.encode('utf-8')))
            headers['content-length'] = content_length
            session.headers.update(headers)
            req = session.post('https://xn--b1afk4ade.xn--90adear.xn--p1ai/proxy/check/auto/restrict', data = encoded_data, timeout = 60)
            data = json.loads(req.text)

            return data
    
        except Exception as e:
            print(e, vin)
            if 'timeout' in str(e):
                data['code'] = 408
                return data



    def parse(self, vin, iteration, result_file):

        start = datetime.datetime.now()

        try:
            data = {}

            session = requests.session()
            proxies = ParserGIBDD.get_proxy()
            session.proxies = proxies

            token, prediction = self.predict(session)

            if token == 0:
                print('Недоступен сервис captcha')
                print(self.token)
                token = self.token
                prediction = self.prediction

            headers = {
                        "accept": "application/json, text/javascript, */*; q=0.01",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5",
                        "cache-control": "no-cache",
                        "connection": "keep-alive",
                        "content-length": '',
                        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "host": "xn--b1afk4ade.xn--90adear.xn--p1ai",
                        "origin": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai",
                        "pragma": "no-cache",
                        "referer": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai/",
                        "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": "\"Windows\"",
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "cross-site",
                        "sec-fetch-storage-access": "active",
                        "user-agent": user_agent.generate_user_agent()
    }
            

            data = ParserGIBDD.reg_data(vin, token, prediction, session, headers)
            
            while 'code' in data.keys():
                if data['code'] == 201 or data['code'] == 408:
                    print('reg retry - ', vin)
                    token, prediction = self.predict(session)
                    data = ParserGIBDD.reg_data(vin, token, prediction, session, headers)
                else:
                    break


            if 'RequestResult' in data.keys():
                periods = data['RequestResult']['periods']
                data = data['RequestResult']
                data.pop('periods')
                for period in periods:
                    line = {**period, **data}

                    line.pop('cday')
                    line.pop('chour')
                    line.pop('cminute')
                    line.pop('cmonth')
                    line.pop('cyear')

                    reg_file = result_file + '_GIBDD_REG.csv'
                    file_exists = os.path.isfile(reg_file)
                    line['VEH_VIN'] = vin
                    print("рег ",line)
                    data_df = pd.DataFrame.from_dict([line]).sort_index(axis=1)

                    
                    with lock:
                        mode = 'a' if file_exists else 'w'
                        header = True if mode == 'w' else False
                        data_df.to_csv(reg_file, mode = mode, header = header, encoding='cp1251', sep=';', index=False)

            else:
                print("ERROR REG")
                print(data)

            print(datetime.datetime.now() - start)
            data = ParserGIBDD.dtp_data(vin, token, prediction, session, headers)

            while 'code' in data.keys():
                if data['code'] == 201 or data['code'] == 408:
                    print('dtp retry - ', vin)
                    token, prediction = self.predict(session)
                    data = ParserGIBDD.dtp_data(vin, token, prediction, session, headers)
                else:
                    break

            if 'RequestResult' in data.keys():
                accidents = data['RequestResult']['Accidents']
                for accident in accidents:
                    accident['DamagePoints'] = ";".join(accident['DamagePoints'])
                    accident['VEH_VIN'] = vin
                    

                    reg_file = result_file + '_GIBDD_DTP.csv'
                    file_exists = os.path.isfile(reg_file)
                    print("дтп ",accident)
                    data_df = pd.DataFrame.from_dict([accident]).sort_index(axis=1)

                    
                    with lock:
                        mode = 'a' if file_exists else 'w'
                        header = True if mode == 'w' else False
                        data_df.to_csv(reg_file, mode = mode, header = header, encoding='cp1251', sep=';', index=False)

            data = ParserGIBDD.limits_data(vin, token, prediction, session, headers)

            while 'code' in data.keys():
                if data['code'] == 201 or data['code'] == 408:
                    print('limits retry - ', vin)
                    token, prediction = self.predict(session)
                    data = ParserGIBDD.limits_data(vin, token, prediction, session, headers)
                else:
                    break

            if 'RequestResult' in data.keys():
                limits = data['RequestResult']['records']
                for limit in limits:
                    limit['VEH_VIN'] = vin
                    reg_file = result_file + '_GIBDD_LIMITS.csv'
                    file_exists = os.path.isfile(reg_file)
                    print('ограничения ',limit)
                    data_df = pd.DataFrame.from_dict([limit]).sort_index(axis=1)

                    
                    with lock:
                        mode = 'a' if file_exists else 'w'
                        header = True if mode == 'w' else False
                        data_df.to_csv(reg_file, mode = mode, header = header, encoding='cp1251', sep=';', index=False)
            print(f'{iteration} - {vin}', flush=True)
            
        except Exception as e:
            print(e)

    
    def worker():

        parser_obj = ParserGIBDD()
        while True:
            try:
                vin, index, result_file = tasks.get(timeout=3)
            except queue.Empty:
                break

            try:
                parser_obj.parse(vin, index, result_file)
            except Exception as e:
                traceback.print_exc()
            finally:
                tasks.task_done()



    def start_GIBDD(file_path):
        #{parent_dir}/init_csv/nb.csv
        init_file_name = file_path.split('/')[-1].split('.')[0]
        data = pd.read_csv(file_path, encoding="cp1251", sep = ';').drop_duplicates().reset_index(drop=True)
        data.fillna('',inplace=True)
        print('...CSV READ COMPLETED...')
        print('...STARTING GIBDD...')
        print(init_file_name)

        parse_date = datetime.datetime.now().strftime('%Y-%m-%d')
        result_file = f'{parent_dir}/result_csv/{init_file_name}'
        rf = result_file + '_GIBDD_REG.csv'
        file_exists = os.path.isfile(rf)
    


        #Логика случай если парсинг в процессе встал или нужна была пауза и нужен перезапуск. Чтобы продолжить с последнего вина
        if file_exists:
            parsed_data = pd.read_csv(rf, encoding="cp1251", sep = ';').fillna('-')
            last_str = parsed_data.iloc[parsed_data.shape[0] - 1]
            data_last_str = data.loc[(data['VEH_VIN'] == last_str['VEH_VIN'])]
            max_index = data_last_str.index.max()
            data = data[data.index > max_index]
        
        random.shuffle(pr)
        for proxy in pr:
            q.put(proxy)

        data['index'] = data.index
        data = data.to_dict(orient='records')
        for row in tqdm(data):
            tasks.put((row['VEH_VIN'], row['index'], result_file))


        threads = []

        for i in range(10):
            thr = threading.Thread(target=ParserGIBDD.worker)
            thr.start()
            threads.append(thr)

        tasks.join()

        for thr in threads:
            thr.join()

ParserGIBDD.start_GIBDD(f'{parent_dir}/init_csv/nb032025.csv')
# ParserGIBDD.start_GIBDD(sys.argv[1])


