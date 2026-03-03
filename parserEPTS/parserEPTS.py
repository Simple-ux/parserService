
import os
import json, requests, sys,  re
import parserEPTS.predict as predict
import traceback
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from parserEPTS.preprocess import Preprocess
from parserEPTS.html_mapping import mapping



parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from baseParser import BaseParser
from factory.modelFactory import modelFactory

class ParserEPTS(BaseParser):

    model = modelFactory.get_model('EPTS')

    @staticmethod
    def parse(params: object) -> dict:
        # vin = 'LGAG3DV22R8848108'
        try:
            vin = params.vin
            session = requests.Session()
            proxies = ParserEPTS.get_proxy()
            headers = {}
            headers['User-Agent'] = generate_user_agent()
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
            headers['Host'] = 'portal.elpts.ru'
            session.headers.update(headers)
            session.proxies = proxies


            req = session.get('https://portal.elpts.ru/portal/home', allow_redirects=True, timeout=5)
            soup = BeautifulSoup(req.text, "html.parser")
            csrf_token = soup.find('meta', attrs={'name': 'csrf-token-value'}).get("content")
            
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            headers['Accept']= 'application/xml, text/xml, */*; q=0.01'
            headers['Referer'] = 'https://portal.elpts.ru/portal/index?0'
            headers['x-csrftoken'] = csrf_token
            headers['x-ajax-token'] = 'b166db68ed94a1899f454ebae489c7b0474c47fd98bd33cbd5982fe56d4d2840'
            headers['x-requested-with'] = 'XMLHttpRequest'
            headers['wicket-ajax'] = 'true'
            headers['Wicket-Ajax-BaseURL'] = 'index?0'
            headers['Wicket-FocusedElementId'] = 'id8'

            session.headers.update(headers)

            session.cookies.set('csrf-token-name', 'csrftoken', domain = 'portal.elpts.ru')
            session.cookies.set('csrf-token-value', csrf_token, domain = 'portal.elpts.ru')
            data = {'identificationNumber' : vin,
                    'id7_hf_0' : '',
                    'csrftoken' : csrf_token,
                    'search' : '1'}
            req = session.post('https://portal.elpts.ru/portal/index?0-1.IBehaviorListener.0-servicesPanel-passportSearchPanel-vinSearchPanel-searchForm-search', data = data, allow_redirects=False, timeout=5)
            pattern = r'<img[^>]*class="captcha-img"[^>]*src="([^"]+)"'
            match = re.search(pattern, req.text)
            if match:
                img_link = match.group(1)
            
            req = session.get(f'https://portal.elpts.ru/portal{img_link[1:]}', timeout=5)
            
            image = req.content
            image_processed = Preprocess.preprocess_image(image)
            solved = predict.predict_captcha(image_processed, ParserEPTS.model)

            data = {'id29_hf_0' : '',
                    'content:result': solved,
                    'csrftoken' : csrf_token,
                    'buttonsContainer:buttons:1' : '1'}
            req = session.post('https://portal.elpts.ru/portal/index?0-1.IBehaviorListener.1-dialog-content-form-buttonsContainer-buttons-1', data = data, timeout=5)

            if 'Вид электронного паспорта' in req.text and 'неверные символы' not in req.text:

                match = re.search(r'<component id="id23" ><!\[CDATA\[(.*?)\]\]></component>', req.text, re.S)
                html_block = match.group(1) if match else ""
                soup = BeautifulSoup(html_block, "html.parser")

                labels = [lbl.get_text(strip=True) for lbl in soup.find_all("label")]
                values = [sp.get_text(strip=True) for sp in soup.find_all("span")]
                data = {mapping.get(lbl, lbl): val for lbl, val in zip(labels, values)}

                return data

            elif 'Недостаточно сведений' in req.text:
                return {
                    'details': 'Не найдено',}
            else:
                print(vin, ' - Capcha error', flush=True)

        except:
            traceback.print_exc()