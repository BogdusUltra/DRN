import socket
import json
import rsa
import base64
import hashlib
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_handshake.py <password>")
        sys.exit(1)
        
    password = sys.argv[1]

    print("[*] Генерация временных RSA-ключей Оркестратора...")
    orch_pub, orch_priv = rsa.newkeys(2048)
    orch_pub_pem = orch_pub.save_pkcs1("PEM").decode('utf-8')

    print("[*] Ждем UDP-маячок от Агента...")
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(('0.0.0.0', 50000))
    
    while True:
        data, addr = udp_sock.recvfrom(4096)
        msg = json.loads(data.decode('utf-8'))
        if msg.get("action") == "beacon":
            agent_ip = addr[0]
            agent_pub_pem = msg.get("public_key")
            agent_name = msg.get("name")
            print(f"[+] Найден Агент '{agent_name}' на {agent_ip}")
            break

    print("[*] Формируем auth_payload...")
    agent_pub = rsa.PublicKey.load_pkcs1(agent_pub_pem.encode('utf-8'))
    
    pub_hash = hashlib.sha256(orch_pub_pem.encode('utf-8')).hexdigest()
    auth_data = json.dumps({"p": password, "h": pub_hash})
    
    encrypted_auth = rsa.encrypt(auth_data.encode('utf-8'), agent_pub)
    auth_payload_b64 = base64.b64encode(encrypted_auth).decode('utf-8')

    handshake_msg = {
        "action": "handshake",
        "orchestrator_pub_key": orch_pub_pem,
        "auth_payload": auth_payload_b64
    }

    print(f"[*] Отправляем Handshake на {agent_ip}:50001...")
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.connect((agent_ip, 50001))
    tcp_sock.sendall(json.dumps(handshake_msg).encode('utf-8'))

    print("[*] Ждем ответ от Агента...")
    resp_data = tcp_sock.recv(4096).decode('utf-8')
    if not resp_data:
        print("[-] Пустой ответ (соединение разорвано)")
        return
        
    resp_json = json.loads(resp_data)
    
    if "encrypted_payload" in resp_json:
        print("[+] Получен зашифрованный ответ. Расшифровываем...")
        enc_b64 = resp_json["encrypted_payload"]
        enc_bytes = base64.b64decode(enc_b64)
        try:
            decrypted = rsa.decrypt(enc_bytes, orch_priv)
            print("[+] Успех! Расшифрованный ответ:")
            print(json.dumps(json.loads(decrypted.decode('utf-8')), indent=4))
        except Exception as e:
            print(f"[-] Ошибка расшифровки: {e}")
    else:
        print("[-] Агент вернул ошибку или некорректный ответ:")
        print(resp_json)

if __name__ == "__main__":
    main()
