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

def handle_client(conn, addr, drn_dir):
    """Обрабатывает входящее TCP-соединение (Handshake и команды)."""
    try:
        data = conn.recv(4096).decode('utf-8')
        if not data:
            return
        
        msg = json.loads(data)
        config_path = os.path.join(drn_dir, "config.json")
        privkey_path = os.path.join(drn_dir, "private.pem")

        if msg.get("action") == "handshake":
            orchestrator_pub = msg.get("orchestrator_pub_key")
            auth_payload_b64 = msg.get("auth_payload")
            
            if not orchestrator_pub or not auth_payload_b64:
                return

            from .crypto import decrypt_rsa, encrypt_rsa, hash_password
            import hashlib
            
            try:
                decrypted_str = decrypt_rsa(auth_payload_b64, privkey_path)
                auth_data = json.loads(decrypted_str)
            except Exception as e:
                # Ошибка расшифровки или неверный формат
                return

            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Проверка пароля
            if hash_password(auth_data.get("p", "")) != config["password_hash"]:
                return
            
            # Проверка привязки (binding) ключа
            pub_hash = hashlib.sha256(orchestrator_pub.encode('utf-8')).hexdigest()
            if auth_data.get("h") != pub_hash:
                return
            
            # Успешная авторизация
            if orchestrator_pub not in config["whitelist"]:
                config["whitelist"].append(orchestrator_pub)
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
            
            # Отправка зашифрованного ответа Оркестратору
            response_json = json.dumps({"status": "ok", "msg": "Handshake successful"})
            encrypted_resp = encrypt_rsa(response_json, orchestrator_pub)
            
            conn.sendall(json.dumps({"encrypted_payload": encrypted_resp}).encode('utf-8'))

        # Обработка команд после Handshake
        if "encrypted_command" in msg:
            from .crypto import decrypt_large_rsa, encrypt_large_rsa
            try:
                decrypted_str = decrypt_large_rsa(msg["encrypted_command"], privkey_path)
                cmd_data = json.loads(decrypted_str)
            except Exception:
                return
            
            with open(config_path, "r") as f:
                config = json.load(f)
            
            orch_pub = cmd_data.get("orchestrator_pub_key")
            response_payload = {"status": "ok"}
            
            # Проверяем, что оркестратор авторизован
            if orch_pub not in config["whitelist"]:
                response_payload = {"status": "error", "error": "Unauthorized"}
            else:
                action = cmd_data.get("action")
                
                if action == "terminal_cmd":
                    cmd = cmd_data.get("cmd")
                    import subprocess
                    try:
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                        response_payload["stdout"] = result.stdout
                        response_payload["stderr"] = result.stderr
                        response_payload["returncode"] = result.returncode
                    except Exception as e:
                        response_payload["error"] = str(e)
                elif action == "echo":
                    response_payload["text"] = cmd_data.get("text")
                else:
                    response_payload["error"] = "Unknown action"
            
            # Шифруем ответ публичным ключом Оркестратора
            enc_resp = encrypt_large_rsa(json.dumps(response_payload), orch_pub)
            conn.sendall(json.dumps({"encrypted_payload": enc_resp}).encode('utf-8'))
    finally:
        conn.close()

def tcp_listener(drn_dir):
    """Слушает TCP порт 50001 для команд и Handshake."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 50001))
    s.listen(5)
    
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr, drn_dir), daemon=True).start()
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
