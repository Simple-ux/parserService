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


class ParserVESSEL(BaseParser):

    @staticmethod
    def parse(params: object) -> dict:
        if params.vessel_num is None:
            raise ValueError("vessel_num parameter is required for VESSEL parser")
        
        session = requests.Session()
        headers = {
                    'User-Agent': user_agent.generate_user_agent()
                }   
        session.headers.update(headers)
        proxy = ParserVESSEL.get_proxy()
        session.proxies = proxy

        resp = session.get(f'https://www.vesselfinder.com/vessels/details/{params.vessel_num}', timeout=10)
        if resp.status_code != 200:
            raise ValueError(f"Failed to fetch data for vessel_num {params.vessel_num}. Status code: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")

        # Находим заголовок секции
        header = soup.find("h2", class_="bar", string="Vessel Particulars")

        data = {}

        if header:
            table = header.find_next("table", class_="tpt1")

            for row in table.select("tr"):
                cols = row.select("td")
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(' ', '_').lower()
                    value = cols[1].get_text(strip=True)
                    data[key] = value

        return data