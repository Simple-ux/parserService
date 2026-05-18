import cv2
import numpy as np


class Preprocess():

    img_w = 200
    
    img_h = 50

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
        # img = np.frombuffer(img, np.uint8)
        # img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        img = cv2.adaptiveThreshold(
                img,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,  # размер окна (нечётный)
                2    # смещение
            )
        
        mask = cv2.Canny(img, 50, 200)
        img = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)

        # cv2.imshow('cap', result)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        return img