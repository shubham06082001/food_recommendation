import joblib


MODEL_PATH = "ml/artifacts/demand_model.joblib"


def load_model():
    return joblib.load(MODEL_PATH)
