import os
import sys
import requests
import pandas as pd
import datetime
import traceback
import threading
import concurrent.futures
import random
import queue

from bs4 import BeautifulSoup
from tqdm import tqdm
import user_agent

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from proxy import proxies

# Блокировка для многопоточной записи
lock = threading.Lock()

writer_q = queue.Queue()


def writer_thread(result_file):
    init_dict = {"data":[]}
    while True:
        if not writer_q.empty():
            init_dict['data'].append(writer_q.get_nowait())

            if len(init_dict['data']) >= 100:
                df = pd.DataFrame.from_records(init_dict)
                mode = 'a' if file_exists else 'w'
                header = not file_exists
                df.to_csv(result_file, mode=mode, header=header, sep=';', encoding='cp1251', index=False)
                file_exists = os.path.isfile(result_file)

        


class ParserFTS:

    q = queue.Queue()
    proxies = proxies

    @staticmethod
    def get_proxy():
        try:
            proxy = ParserFTS.q.get_nowait()
            proxy_splited = proxy.split(':')
            proxy_user = proxy_splited[2]
            proxy_pass = proxy_splited[3]
            proxy_host = proxy_splited[0] + ':' + proxy_splited[1]
            proxies = {
                "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}",
                "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}"
            }
            ParserFTS.q.put(str(proxy))
            return proxies
        except:
            traceback.print_exc()

    @staticmethod
    def parse_vin(vin, result_file = "", index = 0):
        try:

            session = requests.Session()
            session.proxies = ParserFTS.get_proxy()

            headers = {
                'User-Agent': user_agent.generate_user_agent(),
                'Referer': 'https://customs.gov.ru/cars'
            }

            session.headers.update(headers)
            resp_get = session.get('https://customs.gov.ru/cars')
            soup = BeautifulSoup(resp_get.text, 'html.parser')

            token_input = soup.find('input', {'name': '_token'})
            if not token_input:
                raise Exception("Не удалось найти _token")

            xsrf_token = token_input['value']
            payload = {
                '_token': xsrf_token,
                'vin': vin
            }

            resp_post = session.post('https://customs.gov.ru/cars', data=payload)
            soup = BeautifulSoup(resp_post.text, 'html.parser')

            data = {
                'vin': vin,
                'body_number': '-',
                'chassis_number': '-',
                'RELEASE_DATE': '-',
                'country': '-',
                'marka_model': '-',
                'comment': 'Не найдено'
            }

            keys = {
                'номер vin': 'BODY_NUMBER',
                'модель': 'MARKA_MODEL',
                'номер кузова': 'BODY_NUMBER',
                'номер шасси': 'CHASSIS_NUMBER',
                'дата выпуска в свободное обращение': 'RELEASE_DATE'
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
                data['COUNTRY'] = country_code.lower()

            if data['BODY_NUMBER'] != '-' and data['CHASSIS_NUMBER'] != '-':
                data['COMMENT'] = 'Найдено'

            if result_file != 0:
                # file_exists = os.path.isfile(result_file)
                writer_q.put(data)
                print(f"{index} vin-{vin}")
            session.close()

                # with lock:
                #     mode = 'a' if file_exists else 'w'
                #     header = not file_exists
                #     df.to_csv(result_file, mode=mode, header=header, sep=';', encoding='cp1251', index=False)

            return data

        except Exception as e:
            print(f"[ERROR] {vin} - {str(e)}")
            traceback.print_exc()

    @staticmethod
    def start_FTS(file_path):
        init_file_name = file_path.split('/')[-1].split('.')[0]
        result_file = f"{parent_dir}/result_csv/{init_file_name}_FTS.csv"

        df = pd.read_csv(file_path, encoding='cp1251', sep=',').drop_duplicates().fillna('')
        print('...CSV READ COMPLETED...')
        print('...STARTING...', init_file_name)

        if os.path.isfile(result_file):
            parsed = pd.read_csv(result_file, encoding='cp1251', sep=';').fillna('-')
            last = parsed.iloc[-1]
            condition = (df['VEH_VIN'] == last['VEH_VIN'])
            max_index = df[condition].index.max()
            df = df[df.index > max_index]

        random.shuffle(proxies)
        for proxy in proxies:
            q.put(proxy)

        writer = threading.Thread(target=writer_thread, args=(result_file,))
        writer.start()

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = []
            for index, row in df.iterrows():
                futures.append(executor.submit(
                    ParserFTS.parse_vin,
                    vin=str(row['VEH_VIN']),
                    result_file=result_file,
                    index=index
                ))

    
if __name__ == "__main__":
    ParserFTS.start_FTS('init_csv/T23.csv')
    # ParserFTS.start_FTS(sys.argv[1])
