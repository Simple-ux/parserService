import tensorflow as tf
import numpy as np
import cv2
import base64
from io import BytesIO
from parserROSR.preprocess import Preprocess
from factory.modelFactory import modelFactory

# --- настройки такие же как в обучении ---
IMG_WIDTH = 200
IMG_HEIGHT = 50
CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"
num_to_char = {i: c for i, c in enumerate(CHARS)}

def decode_label(encoded):
    return "".join([num_to_char[i] for i in encoded if i != -1])

# --- функция для распознавания ---
def predict_captcha(img):
    model = modelFactory.get_model('ROSR')
    
    nparr = np.frombuffer(img, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    img = Preprocess.preprocess_image(img)
    img = img.astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=-1)   # (H, W, 1)
    img = np.expand_dims(img, axis=0)    # (1, H, W, 1) → батч

    

    # предсказание
    preds = model.predict(img)
    input_len = np.full(shape=(preds.shape[0],), fill_value=preds.shape[1], dtype=np.int32)

    # ctc decode
    decoded, _ = tf.keras.backend.ctc_decode(preds, input_length=input_len)
    pred_text = decode_label(decoded[0][0].numpy())

    return pred_text

# --- пример ---
# print(predict_captcha("dataset/014260.png"))