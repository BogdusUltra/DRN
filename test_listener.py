import socket
import json

def listen_for_beacons():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Разрешаем слушать широковещательные пакеты на порту 50000
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 50000))
    
    print("[*] Тестовый Оркестратор слушает локальную сеть (порт 50000)...")
    print("[*] Ждем маячки от машин...")
    
    while True:
        data, addr = s.recvfrom(4096)
        try:
            msg = json.loads(data.decode('utf-8'))
            if msg.get("action") == "beacon":
                print(f"[{addr[0]}] Найден агент: {msg['name']}")
                # print(f"    Публичный ключ: {msg['public_key'][:60]}...")
        except Exception as e:
            pass

if __name__ == "__main__":
    listen_for_beacons()
