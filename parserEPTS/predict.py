import tensorflow as tf
import numpy as np
import cv2

IMG_WIDTH = 201
IMG_HEIGHT = 60
CHARS = "0123456789"
num_to_char = {i: c for i, c in enumerate(CHARS)}

def decode_label(encoded):
    return "".join([num_to_char[i] for i in encoded if i != -1])


# функция для распознавания 
def predict_captcha(img, prediction_model):
    img = img.astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=-1)   # (H, W, 1)
    img = np.expand_dims(img, axis=0)    # (1, H, W, 1) → батч

    # предсказание
    preds = prediction_model.predict(img)
    input_len = np.full(shape=(preds.shape[0],), fill_value=preds.shape[1], dtype=np.int32)

    # ctc decode
    decoded, _ = tf.keras.backend.ctc_decode(preds, input_length=input_len)
    pred_text = decode_label(decoded[0][0].numpy())

    return pred_text
