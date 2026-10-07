import rsa
import hashlib
import os

def hash_password(password: str) -> str:
    """Хэширует пароль по алгоритму SHA-256 для безопасного хранения."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_keys(save_dir: str):
    """Генерирует пару RSA-ключей (2048 бит) и сохраняет их в указанную директорию."""
    pubkey, privkey = rsa.newkeys(2048)
    
    # Сохраняем публичный ключ
    with open(os.path.join(save_dir, "public.pem"), "wb") as f:
        f.write(pubkey.save_pkcs1("PEM"))
        
    # Сохраняем приватный ключ
    with open(os.path.join(save_dir, "private.pem"), "wb") as f:
        f.write(privkey.save_pkcs1("PEM"))
