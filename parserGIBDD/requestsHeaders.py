import user_agent

captcha_headers = { "Accept": "*/*",
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


data_headers = {
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