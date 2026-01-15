# backend/app/utils.py
from typing import Dict, Any
import json
import joblib
# import tensorflow as tf
# import h5py
# from tensorflow.keras.models import model_from_json

# MODEL_PATH = "app/models/ids_dnn_model.h5"
# SCALER_PATH = "app/models/scaler.pkl"
# FEATURES_PATH = "app/models/feature_names.json"

# tweakable risk weights
ZAP_SEV = {"High": 9.0, "Medium": 5.0, "Low": 2.0, "Info": 0.5}
PORT_RISK = {21: 6.0, 22: 4.0, 23: 7.0, 80: 2.0, 443: 1.0, 3306: 6.0, 3389: 7.0}

def compute_risk(nmap_result: Dict[str, Any], zap_result: Dict[str, Any]) -> float:
    score = 0.0

    try:
        counts = zap_result.get("summary", {}).get("counts", {})
        for k, v in counts.items():
            score += ZAP_SEV.get(k, 1.0) * v
    except Exception:
        pass

    try:
        for host in nmap_result.get("hosts", []):
            for p in host.get("ports", []):
                if p.get("state") == "open":
                    score += PORT_RISK.get(p.get("port", 0), 1.0)
    except Exception:
        pass

    return round(max(0.0, min(10.0, score / 10.0)), 2)


# # ----------------------------------------
# # 🔥 FULL LEGACY KERAS COMPATIBILITY LOADER
# # ----------------------------------------
# def load_legacy_keras_model(model_path: str):
#     with h5py.File(model_path, "r") as f:
#         model_config = json.loads(f.attrs["model_config"])

#     for layer in model_config["config"]["layers"]:
#         cfg = layer.get("config", {})

#         # 1️⃣ Fix InputLayer batch_shape
#         if layer["class_name"] == "InputLayer":
#             if "batch_shape" in cfg:
#                 cfg["input_shape"] = cfg["batch_shape"][1:]
#                 cfg.pop("batch_shape", None)

#         # 2️⃣ REMOVE legacy dtype policies (CRITICAL FIX)
#         if "dtype" in cfg:
#             cfg.pop("dtype", None)

#     # 3️⃣ Build model cleanly
#     model = model_from_json(json.dumps(model_config))

#     # 4️⃣ Load weights
#     model.load_weights(model_path)

#     return model


# # Load model
# model = load_legacy_keras_model(MODEL_PATH)

# # Load scaler
# scaler = joblib.load(SCALER_PATH)

# # Load feature names
# with open(FEATURES_PATH) as f:
#     feature_names = json.load(f)


# # backend/app/utils.py
# from typing import Dict, Any
# import math
# import json
# import joblib
# import tensorflow as tf


# MODEL_PATH = "app/models/ids_dnn_model.h5"
# SCALER_PATH = "app/models/scaler.pkl"
# FEATURES_PATH = "app/models/feature_names.json"

# # tweakable risk weights
# ZAP_SEV = {"High": 9.0, "Medium": 5.0, "Low": 2.0, "Info": 0.5}
# PORT_RISK = {21: 6.0, 22: 4.0, 23: 7.0, 80: 2.0, 443: 1.0, 3306: 6.0, 3389: 7.0}

# def compute_risk(nmap_result: Dict[str, Any], zap_result: Dict[str, Any]) -> float:
#     """
#     Compute a normalized risk score between 0 and 10.
#     - uses counts from ZAP and open ports in Nmap
#     - result is rounded to 2 decimals
#     """
#     score = 0.0
#     try:
#         counts = zap_result.get("summary", {}).get("counts", {})
#         for k, v in counts.items():
#             weight = ZAP_SEV.get(k, 1.0)
#             score += weight * v
#     except Exception:
#         pass

#     try:
#         for host in nmap_result.get("hosts", []):
#             for p in host.get("ports", []):
#                 if p.get("state") == "open":
#                     score += PORT_RISK.get(p.get("port", 0), 1.0)
#     except Exception:
#         pass

#     # Normalize: soft cap using log to avoid extreme values dominating
#     normalized_raw = score / 10.0
#     normalized = max(0.0, min(10.0, normalized_raw))
#     return round(normalized, 2)


# # Load model
# model = tf.keras.models.load_model(
#     MODEL_PATH,
#     compile=False
# )

# # Load scaler
# scaler = joblib.load(SCALER_PATH)

# # Load feature names
# with open(FEATURES_PATH) as f:
#     feature_names = json.load(f)