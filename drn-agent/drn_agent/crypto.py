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

def decrypt_rsa(encrypted_b64: str, privkey_path: str) -> str:
    """Расшифровывает Base64 строку с помощью приватного RSA ключа."""
    import base64
    with open(privkey_path, 'rb') as f:
        privkey = rsa.PrivateKey.load_pkcs1(f.read())
    encrypted_bytes = base64.b64decode(encrypted_b64)
    decrypted_bytes = rsa.decrypt(encrypted_bytes, privkey)
    return decrypted_bytes.decode('utf-8')

def encrypt_rsa(plaintext: str, pubkey_pem: str) -> str:
    """Шифрует строку с помощью публичного RSA ключа (PEM) и возвращает Base64."""
    import base64
    pubkey = rsa.PublicKey.load_pkcs1(pubkey_pem.encode('utf-8'))
    encrypted_bytes = rsa.encrypt(plaintext.encode('utf-8'), pubkey)
    return base64.b64encode(encrypted_bytes).decode('utf-8')
def decrypt_large_rsa(b64_enc: str, privkey_path: str) -> str:
    """Расшифровывает длинные сообщения, разбитые на блоки (chunked RSA)."""
    import base64
    with open(privkey_path, 'rb') as f:
        privkey = rsa.PrivateKey.load_pkcs1(f.read())
    
    data = base64.b64decode(b64_enc)
    # Размер блока RSA-2048 после шифрования всегда 256 байт
    chunks = [data[i:i+256] for i in range(0, len(data), 256)]
    dec_chunks = []
    for chunk in chunks:
        dec_chunks.append(rsa.decrypt(chunk, privkey))
    return b"".join(dec_chunks).decode('utf-8')

def encrypt_large_rsa(plaintext: str, pubkey_pem: str) -> str:
    """Шифрует длинные сообщения блоками для обхода лимита RSA."""
    import base64
    pubkey = rsa.PublicKey.load_pkcs1(pubkey_pem.encode('utf-8'))
    data = plaintext.encode('utf-8')
    # Лимит для 2048-битного ключа (с запасом) = 200 байт
    chunks = [data[i:i+200] for i in range(0, len(data), 200)]
    enc_chunks = []
    for chunk in chunks:
        enc_chunks.append(rsa.encrypt(chunk, pubkey))
    
    full_enc = b"".join(enc_chunks)
    return base64.b64encode(full_enc).decode('utf-8')
