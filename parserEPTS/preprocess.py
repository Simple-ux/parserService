import cv2
import numpy as np



class Preprocess():

    img_w = 201
    
    img_h = 60

    def remove_small_blobs_and_holes(binary_img, min_blob_area=20):
        # Удаление белых шумовых пятен (на чёрном фоне)
        nb_components, output, stats, _ = cv2.connectedComponentsWithStats(binary_img, connectivity=8)
        cleaned = np.zeros(binary_img.shape, dtype=np.uint8)
        for i in range(1, nb_components):  # пропускаем фон (i=0)
            if stats[i, cv2.CC_STAT_AREA] >= min_blob_area:
                cleaned[output == i] = 255

        # Удаление чёрных дыр (внутри белых цифр)
        inv = 255 - cleaned
        nb_components, output, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
        inv_cleaned = np.zeros(inv.shape, dtype=np.uint8)
        for i in range(1, nb_components):
            if stats[i, cv2.CC_STAT_AREA] >= min_blob_area:
                inv_cleaned[output == i] = 255

        return 255 - inv_cleaned

    def extract_contours(img):
        # 1. Преобразуем в градации серого (на всякий случай)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 2. Немного размываем, чтобы убрать шум перед градиентом
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # 3. Выделяем контуры
        edges = cv2.Canny(blurred, threshold1=50, threshold2=150)

        # 4. (Опционально) расширим контуры, чтобы они были ярче
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)

        return edges_dilated

    def preprocess_image(img):
        # Загрузка и преобразование в оттенки серого
        img = np.frombuffer(img, np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Бинаризация
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Инвертировать (если фон чёрный, цифры белые — это лучше для CNN)
        img = 255 - img

        img = Preprocess.remove_small_blobs_and_holes(img)

        img = Preprocess.extract_contours(img)
        
        # Масштабирование с сохранением пропорций и паддинг до нужного размера
        h, w = img.shape
        scale = min(Preprocess.img_w / w, Preprocess.img_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h))
        
        # Добавляем паддинг до нужного размера
        padded = np.ones((Preprocess.img_h, Preprocess.img_w), dtype=np.uint8) * 0  # Чёрный фон
        x_offset = (Preprocess.img_w - new_w) // 2
        y_offset = (Preprocess.img_h - new_h) // 2
        padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = img

        # cv2.imshow('cap', padded)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        return padded