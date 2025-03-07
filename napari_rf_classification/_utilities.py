
import pickle

def save_model(data, path):
    with open(path, 'wb') as file:
        pickle.dump(data, file)

def load_model(path):
    with open(path, 'rb') as file:
        data = pickle.load(file)
    model = data.pop("model")
    return model, data

def wrap_api(func):
    func.__module__ = "napari_rf_classification"
    return func
