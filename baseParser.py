from abc import ABC, abstractmethod
import random
from proxy import proxies
import queue


class BaseParser(ABC):
    proxies = proxies
    proxy_gen = None

    #Метод, который должен быть реализован в каждом парсере
    @abstractmethod
    def parse(self, params: object) -> dict:
        pass

    # Генератор прокси для циклического перебора
    @classmethod
    def proxy_generator(cls):
        while True:
            for proxy in cls.proxies:
                yield proxy

    # Получение прокси
    @classmethod
    def get_proxy(cls, format="requests"):
        if cls.proxy_gen is None:
            cls.proxy_gen = cls.proxy_generator()
            
        proxy = next(cls.proxy_gen)
        proxy_splited = proxy.split(':')
        proxy_user = proxy_splited[2]
        proxy_pass = proxy_splited[3]
        proxy_host = proxy_splited[0] + ':' + proxy_splited[1]
        if format == "requests":
            proxies = {
                "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}",
                "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}"
            }
        elif format == "httpx":
            proxies= {  "http://": f"http://{proxy_user}:{proxy_pass}@{proxy_host}",
                        "https://": f"http://{proxy_user}:{proxy_pass}@{proxy_host}"}
        else:
            raise ValueError("Unsupported proxy format")
        return proxies
    
    
    @classmethod
    def thread_worker(cls, model):
        return
    
