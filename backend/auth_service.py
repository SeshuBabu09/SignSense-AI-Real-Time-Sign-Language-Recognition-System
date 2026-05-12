import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def register_user(email, password, domain):
    users = load_users()
    email = email.strip().lower()

    if any(u["email"] == email for u in users):
        return False, "Email already registered"

    if domain not in ["deaf", "blind"]:
        return False, "Invalid domain"

    hashed = generate_password_hash(password)

    users.append({
        "email": email,
        "password": hashed,
        "domain": domain
    })
    save_users(users)

    return True, "Registered successfully"


def login_user(email, password):
    users = load_users()
    email = email.strip().lower()

    for u in users:
        if u["email"] == email:
            if check_password_hash(u["password"], password):
                return True, u["domain"]
            return False, "Wrong password"

    return False, "User not found"
