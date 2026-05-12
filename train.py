import os
import pickle
import numpy as np
from collections import Counter

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# =========================
# SETTINGS
# =========================
DATA_PICKLE = "./data.pickle"

# ✅ AUTO SAVE MODEL INTO BACKEND FOLDER
MODEL_SAVE = "./backend/model.p"

TOTAL_FEATURES = 84  # ✅ Left(42) + Right(42)

# =========================
# Load dataset
# =========================
if not os.path.exists(DATA_PICKLE):
    raise FileNotFoundError("❌ data.pickle not found. Run create_dataset.py first.")

data_dict = pickle.load(open(DATA_PICKLE, "rb"))

X = np.asarray(data_dict["data"], dtype=np.float32)
y = np.asarray(data_dict["labels"])

print("✅ Loaded dataset")
print("📌 Samples:", X.shape[0])
print("📌 Features per sample:", X.shape[1])

# Validate features
if X.shape[1] != TOTAL_FEATURES:
    raise ValueError(
        f"❌ Feature mismatch: dataset has {X.shape[1]} features but expected {TOTAL_FEATURES}.\n"
        f"✅ Fix: Run updated create_dataset.py again."
    )

# =========================
# Show class counts
# =========================
counter = Counter(y)
print("\n📊 Samples per class:")
for k in sorted(counter.keys()):
    print(f"  {k:15s} -> {counter[k]}")

# Warn low samples
low_classes = [k for k, v in counter.items() if v < 20]
if low_classes:
    print("\n⚠️ WARNING: Low sample classes (<20):", low_classes)
    print("   Accuracy for these may be unstable.\n")

# =========================
# Split
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    shuffle=True,
    stratify=y,
    random_state=42
)

print("\n✅ Train/Test split done")
print("📌 Train:", len(X_train))
print("📌 Test :", len(X_test))

# =========================
# Train model
# =========================
print("\n🚀 Training model...")

model = RandomForestClassifier(
    n_estimators=500,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# =========================
# Evaluate
# =========================
print("\n🧪 Testing...")

pred = model.predict(X_test)
acc = accuracy_score(y_test, pred)
print(f"🎯 Accuracy: {acc*100:.2f}%")

print("\n📊 Classification report:\n")
print(classification_report(y_test, pred, zero_division=0))

# =========================
# Save model (AUTO backend folder)
# =========================
os.makedirs("./backend", exist_ok=True)

with open(MODEL_SAVE, "wb") as f:
    pickle.dump(
        {"model": model, "classes": model.classes_, "feature_size": TOTAL_FEATURES},
        f
    )

print(f"\n✅ Model saved -> {MODEL_SAVE}")
print("✅ Now run: python backend/app.py OR python backend/inference_service.py\n")
