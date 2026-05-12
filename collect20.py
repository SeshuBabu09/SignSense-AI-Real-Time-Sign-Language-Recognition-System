import os
import cv2
import time
from cvzone.HandTrackingModule import HandDetector

# ----------------------------
# SETTINGS
# ----------------------------
DATA_DIR = "./Data"
IMG_SIZE = 200
PADDING = 20

# ✅ 20 Emergency Needs Signs (extend here anytime)
SIGNS = [
    "HELP", "EMERGENCY", "CALL", "POLICE", "AMBULANCE",
    "HOSPITAL", "DOCTOR", "MEDICINE", "PAIN", "INJURY",
    "BLEEDING", "FIRE", "DANGER", "STOP", "RUN",
    "WATER", "FOOD", "YES", "NO", "HOME"
]

AUTO_SAVE_DELAY = 0.20  # Auto-save speed

# ----------------------------
# Create folders automatically
# ----------------------------
os.makedirs(DATA_DIR, exist_ok=True)
for sign in SIGNS:
    os.makedirs(os.path.join(DATA_DIR, sign), exist_ok=True)

# ----------------------------
# Camera + detector
# ----------------------------
cap = cv2.VideoCapture(0)
detector = HandDetector(maxHands=2, detectionCon=0.65)

if not cap.isOpened():
    raise RuntimeError("❌ Camera not opening. Check webcam permission.")

selected_index = 0
selected_label = SIGNS[selected_index]
save_count = 0

auto_save = False
last_auto_save_time = 0

def safe_crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(w, x2); y2 = min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]

def save_crop(crop_img, label):
    global save_count
    crop_resized = cv2.resize(crop_img, (IMG_SIZE, IMG_SIZE))
    filename = f"{int(time.time()*1000)}.jpg"
    save_path = os.path.join(DATA_DIR, label, filename)
    cv2.imwrite(save_path, crop_resized)
    save_count += 1
    print("✅ Saved:", save_path)

print("\n✅ Emergency Signs Collection Started")
print("Controls:")
print("  N = Next sign")
print("  B = Previous sign")
print("  S = Save image")
print("  A = Auto-save ON/OFF")
print("  Q / ESC = Quit\n")

while True:
    ok, img = cap.read()
    if not ok:
        break

    img = cv2.flip(img, 1)
    H, W = img.shape[:2]

    hands, _ = detector.findHands(img, draw=False)
    crop_for_save = None
    mode_text = ""

    if hands:
        # ✅ crop includes 1 hand or 2 hands together
        x_min = min([h["bbox"][0] for h in hands])
        y_min = min([h["bbox"][1] for h in hands])
        x_max = max([h["bbox"][0] + h["bbox"][2] for h in hands])
        y_max = max([h["bbox"][1] + h["bbox"][3] for h in hands])

        x1, y1 = x_min - PADDING, y_min - PADDING
        x2, y2 = x_max + PADDING, y_max + PADDING

        cv2.rectangle(img, (max(0, x1), max(0, y1)), (min(W, x2), min(H, y2)), (0, 255, 0), 3)

        crop_for_save = safe_crop(img, x1, y1, x2, y2)
        mode_text = "ONE HAND" if len(hands) == 1 else "TWO HANDS"

    # UI
    cv2.putText(img, f"Label [{selected_index+1}/{len(SIGNS)}]: {selected_label}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 3)

    cv2.putText(img, f"Saved: {save_count}", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

    cv2.putText(img, f"Auto-save: {'ON' if auto_save else 'OFF'}", (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (0, 0, 255) if auto_save else (120, 120, 120), 2)

    if mode_text:
        cv2.putText(img, mode_text, (20, 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    cv2.imshow("Collect Emergency Signs", img)
    if crop_for_save is not None:
        cv2.imshow("Crop Preview", crop_for_save)

    key = cv2.waitKey(1) & 0xFF

    if key in [27, ord("q"), ord("Q")]:
        break

    if key in [ord("n"), ord("N")]:
        selected_index = (selected_index + 1) % len(SIGNS)
        selected_label = SIGNS[selected_index]
        print("✅ Selected:", selected_label)

    if key in [ord("b"), ord("B")]:
        selected_index = (selected_index - 1) % len(SIGNS)
        selected_label = SIGNS[selected_index]
        print("✅ Selected:", selected_label)

    if key in [ord("s"), ord("S")]:
        if crop_for_save is None or crop_for_save.size == 0:
            print("⚠️ No hand crop to save.")
        else:
            save_crop(crop_for_save, selected_label)

    if key in [ord("a"), ord("A")]:
        auto_save = not auto_save
        print(f"✅ Auto-save {'ON' if auto_save else 'OFF'}")

    # Auto-save
    if auto_save and crop_for_save is not None and crop_for_save.size != 0:
        now = time.time()
        if (now - last_auto_save_time) >= AUTO_SAVE_DELAY:
            save_crop(crop_for_save, selected_label)
            last_auto_save_time = now

cap.release()
cv2.destroyAllWindows()
print("✅ Done collecting.")
