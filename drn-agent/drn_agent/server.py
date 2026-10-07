import socket
import threading
import time
import json
import os

def udp_beacon(drn_dir):
    """Фоновый поток: шлет широковещательные пакеты, пока машина не авторизована."""
    config_path = os.path.join(drn_dir, "config.json")
    pubkey_path = os.path.join(drn_dir, "public.pem")

    with open(config_path, "r") as f:
        config = json.load(f)
    with open(pubkey_path, "r") as f:
        pubkey = f.read()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    payload = json.dumps({
        "action": "beacon",
        "name": config["name"],
        "public_key": pubkey
    }).encode('utf-8')

    print("[*] Поток UDP-Маячка запущен (порт 50000)...")
    while True:
        # В будущем: проверять, пустой ли whitelist, и если нет - останавливать маячок
        try:
            s.sendto(payload, ('255.255.255.255', 50000))
        except Exception as e:
            pass
        time.sleep(2)

def tcp_listener(drn_dir):
    """Основной поток: слушает TCP порт 50001 для команд и Handshake."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Позволяет переиспользовать порт после перезапуска
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 50001))
    s.listen(5)
    
    print("[*] TCP Сервер запущен. Ожидание команд на порту 50001...")
    
    while True:
        conn, addr = s.accept()
        print(f"[+] Входящее TCP подключение от: {addr[0]}")
        # Здесь позже напишем логику приема Handshake и проверки подписи
        conn.close()

def start_agent_daemon():
    home_dir = os.path.expanduser("~")
    drn_dir = os.path.join(home_dir, ".drn_agent")
    
    if not os.path.exists(drn_dir):
        print("[-] Ошибка: Агент не инициализирован. Выполните 'drn init' сначала.")
        return

    # Запускаем маячок в отдельном фоновом потоке
    beacon_thread = threading.Thread(target=udp_beacon, args=(drn_dir,), daemon=True)
    beacon_thread.start()

    # Запускаем TCP сервер в главном потоке
    tcp_listener(drn_dir)
