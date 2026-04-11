import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 260000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")

    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )

    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(derived).decode("utf-8")
    return f"{ALGORITHM}${ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, hash_b64 = password_hash.split("$", 3)
        if algorithm != ALGORITHM:
            return False

        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        stored_hash = base64.b64decode(hash_b64.encode("utf-8"))

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(derived, stored_hash)
    except Exception:
        return False


def authenticate_user(user_repo, username: str, password: str):
    if not username or not password:
        return None, "Username and password are required."

    user = user_repo.get_by_username(username.strip())
    if user is None:
        return None, "Invalid username or password."

    if not user.is_active:
        return None, "This account is inactive."

    if not verify_password(password, user.password_hash):
        return None, "Invalid username or password."

    return user, None