import requests
import json
import base64
import cv2
import numpy as np
import concurrent.futures
import pandas as pd
import traceback, random
import datetime, queue, sys, os, threading, json
import time
from io import BytesIO
from tensorflow import keras
from tensorflow.keras import layers, models, backend as K
from PIL import Image
from urllib.parse import urlencode


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
from baseParser import BaseParser
from parserGIBDD.requestsHeaders import captcha_headers, data_headers



class ParserGIBDD(BaseParser):
    session = ''
    token = ''
    captcha = ''

    @staticmethod
    def decode_predictions(pred, beam_width=5):
        decoded, _ = K.ctc_decode(pred, input_length=np.ones(pred.shape[0]) * pred.shape[1], greedy=True)
        out = K.get_value(decoded[0])
        results = []
        for seq in out:
            results.append(''.join([str(ch) for ch in seq if ch != -1]))
        return results
    

    #Предсказание капчи и апдейт токена в сессии каждые 30-60 секунд
    @classmethod
    def thread_worker(cls, model):
        print(f'Started thread for GIBDD parser')
        while True:
            
            session = requests.session()
            session.proxies = cls.get_proxy()
            
            token = ''
            prediction = ''
            
            try:
                session.headers.clear()
                session.headers.update(captcha_headers)

                req = session.get('https://check.gibdd.ru/captcha', proxies=session.proxies, timeout=30)
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

                data = ParserGIBDD.reg_data('ZFA263000M6U12144', token, prediction[0], session, data_headers)
            
                if 'code' in data.keys():
                    if data['code'] == 201 or data['code'] == 408:
                        print('captcha GIBDD retrying in thread')
                        continue

                cls.token = token
                cls.prediction = prediction[0]
                cls.session = session

                print('GIBDD xsrf token has been updated', cls.prediction)

                time.sleep(random.randint(120, 180))
                
            except Exception as e:
                print("GIBDD",e)
                time.sleep(5)
                continue

            

            
            
    
    @classmethod
    def parse(cls, params):

        try:
            data = {}
            result = {}
            result['data'] = {}

            token = cls.token
            prediction = cls.prediction
            session = cls.session

            if params.vin:
                vin = params.vin
            else:
                vin = None
                raise ValueError("VIN номер не указан")
            
            
            # data = ParserGIBDD.reg_data(vin, token, prediction, session, data_headers)
            # line = {}
            # if 'RequestResult' in data.keys():
            #     periods = data['RequestResult']['periods']
            #     data = data['RequestResult']
            #     data.pop('periods')
            #     for period in periods:
            #         line = {**period, **data}

            #         line.pop('cday')
            #         line.pop('chour')
            #         line.pop('cminute')
            #         line.pop('cmonth')
            #         line.pop('cyear')

            #         line['veh_vin'] = vin

                    
            # else:
            #     print("ERROR REG")
            #     raise ValueError("Ошибка при получении регистрационных данных")

            # result['data']['registration'] = line

            data = ParserGIBDD.dtp_data(vin, token, prediction, session, data_headers)
            if 'RequestResult' in data.keys():
                accidents = []
                accidents = data['RequestResult']['Accidents']
                for accident in accidents:
                    accident['DamagePoints'] = ";".join(accident['DamagePoints'])
                    accident['veh_vin'] = vin
                result['data']['accidents'] = accidents


            data = ParserGIBDD.limits_data(vin, token, prediction, session, data_headers)
            if 'RequestResult' in data.keys():
                limits = []
                limits = data['RequestResult']['records']
                for limit in limits:
                    limit['veh_vin'] = vin
                result['data']['limits'] = limits
            
            result['data']['vin'] = vin
            return result
            
        except Exception as e:
            raise ValueError(e)

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