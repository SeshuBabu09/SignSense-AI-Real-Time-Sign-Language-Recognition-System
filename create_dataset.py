import os
import cv2
import pickle
import mediapipe as mp
from collections import Counter

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

DATA_DIR = "./Data"
OUT_PICKLE = "data.pickle"

FEATURES_PER_HAND = 42
TOTAL_FEATURES = 84

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.3)

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

    return out  # 42

data, labels = [], []

if not os.path.exists(DATA_DIR):
    raise FileNotFoundError(f"❌ Data folder not found: {DATA_DIR}")

class_names = sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])
if not class_names:
    raise RuntimeError("❌ No class folders found inside Data/")

print("✅ Classes:", class_names)

for label in class_names:
    folder = os.path.join(DATA_DIR, label)
    imgs = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    print(f"📌 {label} -> {len(imgs)} images")

    for fn in imgs:
        path = os.path.join(folder, fn)
        img = cv2.imread(path)
        if img is None:
            continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        if not results.multi_hand_landmarks:
            continue

        # default zeros if missing hand
        left_feat = [0.0] * FEATURES_PER_HAND
        right_feat = [0.0] * FEATURES_PER_HAND

        if results.multi_handedness:
            for idx, handed in enumerate(results.multi_handedness):
                side = handed.classification[0].label  # Left / Right
                feat = extract_one_hand(results.multi_hand_landmarks[idx])
                if len(feat) != FEATURES_PER_HAND:
                    continue
                if side == "Left":
                    left_feat = feat
                else:
                    right_feat = feat
        else:
            # fallback
            feat = extract_one_hand(results.multi_hand_landmarks[0])
            if len(feat) == FEATURES_PER_HAND:
                right_feat = feat

        full = left_feat + right_feat  # 84
        if len(full) == TOTAL_FEATURES:
            data.append(full)
            labels.append(label)

print("\n✅ Total Samples:", len(data))
print("✅ Total Classes:", len(set(labels)))

counter = Counter(labels)
print("\n📊 Samples per class:")
for k in sorted(counter.keys()):
    print(f"  {k:15s} -> {counter[k]}")

with open(OUT_PICKLE, "wb") as f:
    pickle.dump(
        {"data": data, "labels": labels, "classes": class_names, "feature_size": TOTAL_FEATURES},
        f
    )

print(f"\n✅ Saved successfully: {OUT_PICKLE}")
