import os
import cv2
import time
import pickle
import numpy as np
import mediapipe as mp
import pyttsx3
from collections import deque, Counter
from cvzone.HandTrackingModule import HandDetector

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

MODEL_PATH = "./model.p"
PADDING = 20

FEATURES_PER_HAND = 42
TOTAL_FEATURES = 84

CONFIDENCE_THRESHOLD = 0.70
SMOOTH_FRAMES = 15
SPEAK_COOLDOWN = 1.8

prediction_buffer = deque(maxlen=SMOOTH_FRAMES)

# Load model
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("❌ model.p not found. Train first: python train.py")

with open(MODEL_PATH, "rb") as f:
    model_dict = pickle.load(f)

model = model_dict["model"]
feature_size = int(model_dict.get("feature_size", TOTAL_FEATURES))

if feature_size != TOTAL_FEATURES:
    raise ValueError(f"❌ model feature mismatch: {feature_size} vs {TOTAL_FEATURES}. Retrain model.")

print("✅ Model Loaded (1-hand + 2-hand emergency signs)")

# TTS
engine = pyttsx3.init()
engine.setProperty("rate", 160)
engine.setProperty("volume", 1.0)
last_spoken = ""
last_spoken_time = 0

# Camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("❌ Camera not opening.")

detector = HandDetector(maxHands=2, detectionCon=0.65)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mpHands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

def safe_crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]

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

    return out

def predict(sample):
    pred = model.predict(sample)[0]
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(sample)[0]
        conf = float(np.max(proba))
    else:
        conf = 1.0
    return str(pred), conf

print("🎥 Running... Press Q to quit.")

while True:
    ok, img = cap.read()
    if not ok:
        break

    img = cv2.flip(img, 1)
    H, W = img.shape[:2]

    hands, _ = detector.findHands(img, draw=False)

    prediction_text = "No Hand"
    confidence_text = ""
    mode_text = ""

    crop_window = None

    if hands:
        # crop includes 1 hand or 2 hands
        x_min = min([h["bbox"][0] for h in hands])
        y_min = min([h["bbox"][1] for h in hands])
        x_max = max([h["bbox"][0] + h["bbox"][2] for h in hands])
        y_max = max([h["bbox"][1] + h["bbox"][3] for h in hands])

        x1, y1 = x_min - PADDING, y_min - PADDING
        x2, y2 = x_max + PADDING, y_max + PADDING

        cv2.rectangle(img, (max(0, x1), max(0, y1)), (min(W, x2), min(H, y2)), (0, 255, 0), 3)

        crop = safe_crop(img, x1, y1, x2, y2)
        crop_window = crop

        mode_text = "ONE HAND" if len(hands) == 1 else "TWO HANDS"

        if crop is not None and crop.size != 0:
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            results = mpHands.process(crop_rgb)

            left_feat = [0.0] * FEATURES_PER_HAND
            right_feat = [0.0] * FEATURES_PER_HAND

            if results.multi_hand_landmarks and results.multi_handedness:
                for idx, handed in enumerate(results.multi_handedness):
                    side = handed.classification[0].label
                    feat = extract_one_hand(results.multi_hand_landmarks[idx])

                    if len(feat) != FEATURES_PER_HAND:
                        continue

                    if side == "Left":
                        left_feat = feat
                    else:
                        right_feat = feat

                full = left_feat + right_feat
                sample = np.asarray(full, dtype=np.float32).reshape(1, -1)
                pred, conf = predict(sample)

                if conf >= CONFIDENCE_THRESHOLD:
                    prediction_buffer.append(pred)
                    final_pred = Counter(prediction_buffer).most_common(1)[0][0]
                    prediction_text = final_pred
                    confidence_text = f"{int(conf * 100)}%"
                else:
                    prediction_text = "Unclear"
                    confidence_text = f"{int(conf * 100)}%"

            # draw landmarks
            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(crop, lm, mp_hands.HAND_CONNECTIONS)

    # Speak
    now = time.time()
    if prediction_text not in ["No Hand", "Unclear"]:
        if prediction_text != last_spoken and (now - last_spoken_time) > SPEAK_COOLDOWN:
            try:
                engine.say(prediction_text.replace("_", " "))
                engine.runAndWait()
            except:
                pass
            last_spoken = prediction_text
            last_spoken_time = now

    # UI
    if mode_text:
        cv2.putText(img, f"Mode: {mode_text}", (20, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    cv2.putText(img, f"Prediction: {prediction_text}", (20, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

    if confidence_text:
        cv2.putText(img, f"Confidence: {confidence_text}", (20, 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

    cv2.imshow("Emergency Signs (1-Hand / 2-Hand)", img)
    if crop_window is not None:
        cv2.imshow("Landmarks View", crop_window)

    key = cv2.waitKey(1) & 0xFF
    if key in [ord("q"), ord("Q"), 27]:
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Done.")
