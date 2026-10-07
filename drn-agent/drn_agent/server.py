import socket
import threading
import time
import json
import os

def udp_beacon(drn_dir):
    """Фоновый поток: шлет широковещательные пакеты."""
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

    interval = config.get("beacon_interval", 2)

    while True:
        try:
            s.sendto(payload, ('255.255.255.255', 50000))
        except Exception:
            pass
        time.sleep(interval)

def tcp_listener(drn_dir):
    """Слушает TCP порт 50001 для команд и Handshake."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 50001))
    s.listen(5)
    
    while True:
        try:
            conn, addr = s.accept()
            # Заглушка для обработки соединений
            conn.close()
        except Exception:
            pass

def start_agent_daemon(drn_dir):
    """Главная функция фонового процесса. Запускает потоки и удерживает жизнь скрипта."""
    if not os.path.exists(drn_dir):
        return

    beacon_thread = threading.Thread(target=udp_beacon, args=(drn_dir,), daemon=True)
    beacon_thread.start()

    tcp_thread = threading.Thread(target=tcp_listener, args=(drn_dir,), daemon=True)
    tcp_thread.start()

    # Бесконечный цикл, чтобы процесс не завершился сам по себе
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
