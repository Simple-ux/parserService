import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import base64
from io import BytesIO
import cv2
import numpy as np
from random import randrange


def captcha(captcha_url):
    captcha_url_base_64 = captcha_url.split(",")[1].replace('\n', '')
    img_data = BytesIO(base64.b64decode(captcha_url_base_64))
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
        if area > 200:
            cv2.drawContours(mask, [cnt], -1, 255, -1)

    img = cv2.bitwise_and(img, mask)

    # kernel = np.ones((1, 1), np.uint8)  # Ядро 2x2 (можно увеличить для сильного шума)
    # img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=1)


    img = cv2.bitwise_not(img)


    


    print(text)
    

    cv2.imwrite(f'parserGIBDD/captcha.png', img)




