import tensorflow as tf
import numpy as np
import soundfile as sf
import os, io

# === Константы ===
SAMPLE_RATE = 8000
CHARS = list("0123456789")
char_to_num = {ch: i + 1 for i, ch in enumerate(CHARS)}  # 0 = blank
num_to_char = {v: k for k, v in char_to_num.items()}
VOCAB_SIZE = len(char_to_num) + 1  # +1 for blank

# === Преобразование аудио ===
def preprocess_audio(wav_bytes):
    audio, sr = sf.read(io.BytesIO(wav_bytes))
    if sr != SAMPLE_RATE:
        raise ValueError(f"Неверная частота: {sr}")
    target_len = SAMPLE_RATE * 9
    if len(audio) > target_len:
        audio = audio[:target_len]
    else:
        audio = np.pad(audio, (0, target_len - len(audio)))
    audio_tensor = tf.convert_to_tensor(audio, dtype=tf.float32)
    spectrogram = tf.signal.stft(audio_tensor, frame_length=256, frame_step=128)
    spectrogram = tf.abs(spectrogram)
    spectrogram = tf.math.log(spectrogram + 1e-6)
    return tf.expand_dims(spectrogram, -1)  # (time, freq, 1)

# === Декодирование предсказания ===
def decode_prediction(pred):
    decoded, _ = tf.keras.backend.ctc_decode(pred, input_length=[pred.shape[1]], greedy=True)
    decoded_seq = decoded[0][0].numpy()
    return ''.join(num_to_char.get(i, '') for i in decoded_seq if i > 0)

# === Функция предсказания на основе обычной модели ===
def predict(wav_bytes, model):
    spec = preprocess_audio(wav_bytes)
    spec = tf.expand_dims(spec, axis=0)  # batch dim
    pred = model(spec, training=False)
    text = decode_prediction(pred)
    return text


# === Функция предсказания на основе облегченной модели ===
def predict_tflite(wav_bytes, model):
    # Загрузка TFLite модели
    model.allocate_tensors()

    input_details = model.get_input_details()
    output_details = model.get_output_details()

    # Подготовка входа
    spec = preprocess_audio(wav_bytes)
    input_tensor = np.expand_dims(spec, axis=0)  # add batch dim

    model.set_tensor(input_details[0]['index'], input_tensor)
    model.invoke()

    output_data = model.get_tensor(output_details[0]['index'])  # (1, time, vocab)
    pred = output_data[0]  # remove batch dim

    return decode_prediction(np.expand_dims(pred, axis=0))