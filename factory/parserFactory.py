from parserFTS.parserFTS import ParserFTS
from parserNSIS.parserNSIS import ParserNSIS
from parserGIBDD.parserGIBDD import ParserGIBDD
from parserEPTS.parserEPTS import ParserEPTS
from parserFSSP.parserFSSP import ParserFSSP
from parserROSR.parserROSR import ParserROSR


class parserFactory:

    #Список классов всех парсеров
    parsers = {
        'FTS': ParserFTS,
        'NSIS': ParserNSIS,
        'GIBDD': ParserGIBDD,
        'EPTS': ParserEPTS,
        'ROSR': ParserROSR,
        'FSSP': ParserFSSP
        }
    
    thread_workers_count = {
        'FTS': 3,
        'NSIS': 1,
        'GIBDD': 1,
        'EPTS': 1,
        'ROSR': 3,
        'FSSP': 1
    }
    
    @classmethod
    def get_parser(cls, name: str):
        parser_class = cls.parsers.get(name)
        if not parser_class:
            raise ValueError(f"Parser '{name}' not found.")
        return parser_class
    
    