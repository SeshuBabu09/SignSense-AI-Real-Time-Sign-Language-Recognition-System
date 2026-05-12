import os
import cv2
import pickle
import numpy as np
import mediapipe as mp
from cvzone.HandTrackingModule import HandDetector

# =========================
# SETTINGS
# =========================
PADDING = 20

CONFIDENCE_THRESHOLD = 0.50  # 50%
NOISE_THRESHOLD = 0.20       # below this -> unclear

FEATURES_PER_HAND = 42
TOTAL_FEATURES = 84  # Left(42) + Right(42)

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.p")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"❌ model.p not found at: {MODEL_PATH}\n"
        f"✅ Put model.p inside backend folder."
    )

# =========================
# LOAD MODEL
# =========================
with open(MODEL_PATH, "rb") as f:
    model_dict = pickle.load(f)

model = model_dict["model"]
print("✅ Model loaded:", MODEL_PATH)

# =========================
# MEDIAPIPE
# =========================
mp_hands = mp.solutions.hands
mpHands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.70,
    min_tracking_confidence=0.70
)

# =========================
# CVZONE
# =========================
detector = HandDetector(maxHands=2, detectionCon=0.70)

def safe_crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None, (x1, y1, x2, y2)
    return img[y1:y2, x1:x2], (x1, y1, x2, y2)

def extract_one_hand(hand_landmarks):
    x_list, y_list, out = [], [], []
    for lm in hand_landmarks.landmark:
        x_list.append(lm.x)
        y_list.append(lm.y)

    min_x = min(x_list)
    min_y = min(y_list)

    for lm in hand_landmarks.landmark:
        out.append(lm.x - min_x)
        out.append(lm.y - min_y)

    return out  # length = 42

def predict_with_conf(sample):
    pred = model.predict(sample)[0]
    conf = 1.0
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(sample)[0]
        conf = float(np.max(proba))
    return str(pred), conf

class SignRecognizer:
    def __init__(self, cam_index=0):
        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not self.cap.isOpened():
            raise RuntimeError("❌ Camera not opening. Check webcam permission.")

    def read_frame(self):
        ok, img = self.cap.read()
        if not ok:
            return None, {"prediction": "Camera Error", "confidence": 0.0, "hand": "None"}

        img = cv2.flip(img, 1)

        prediction_text = "No Hand"
        conf = 0.0
        hand_mode = "None"

        hands, _ = detector.findHands(img, draw=False)

        if hands:
            hand_mode = "OneHand" if len(hands) == 1 else "TwoHands"

            x_min = min([h["bbox"][0] for h in hands])
            y_min = min([h["bbox"][1] for h in hands])
            x_max = max([h["bbox"][0] + h["bbox"][2] for h in hands])
            y_max = max([h["bbox"][1] + h["bbox"][3] for h in hands])

            imgCrop, (x1, y1, x2, y2) = safe_crop(
                img,
                x_min - PADDING, y_min - PADDING,
                x_max + PADDING, y_max + PADDING
            )

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 4)

            if imgCrop is not None and imgCrop.size != 0:
                crop_rgb = cv2.cvtColor(imgCrop, cv2.COLOR_BGR2RGB)
                results = mpHands.process(crop_rgb)

                left_feat = [0.0] * FEATURES_PER_HAND
                right_feat = [0.0] * FEATURES_PER_HAND

                if results.multi_hand_landmarks and results.multi_handedness:
                    for idx, handed in enumerate(results.multi_handedness):
                        side = handed.classification[0].label  # "Left"/"Right"
                        feat = extract_one_hand(results.multi_hand_landmarks[idx])

                        if len(feat) != FEATURES_PER_HAND:
                            continue

                        if side == "Left":
                            left_feat = feat
                        else:
                            right_feat = feat

                    full_feat = left_feat + right_feat
                    sample = np.asarray(full_feat, dtype=np.float32).reshape(1, -1)

                    pred, conf = predict_with_conf(sample)

                    # ✅ Noise protection
                    if conf < NOISE_THRESHOLD:
                        prediction_text = "Unclear"
                    else:
                        prediction_text = pred

        # Overlay
        cv2.putText(img, f"Mode: {hand_mode}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.putText(img, f"Prediction: {prediction_text}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        cv2.putText(img, f"Confidence: {int(conf*100)}%", (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        status = {
            "prediction": prediction_text,
            "confidence": float(conf),  # 0..1 float
            "hand": hand_mode
        }

        return img, status

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
