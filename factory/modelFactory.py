
import  urllib3
import tensorflow as tf
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



class modelFactory:

    models = {
        'GIBDD': tf.keras.models.load_model('models/model_GIBDD.keras', compile=False),
        'EPTS': tf.keras.models.load_model('models/model_EPTS.keras', compile=False),
        'FSSP': tf.lite.Interpreter(model_path="models/model_FSSP.tflite")
    }
    
    @classmethod
    def get_model(cls, name: str):
        model = cls.models.get(name)
        if not model:
            print(f"Model '{name}' not found or doesn't needed.") 
            return None
        return model