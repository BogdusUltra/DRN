import socket
import json
import rsa
import base64
import hashlib

class DRNClient:
    """Обертка для связи с Агентами (Handshake и отправка команд)"""
    def __init__(self):
        # Временные ключи для Оркестратора (в будущем будут загружаться из файла)
        self.pub, self.priv = rsa.newkeys(2048)
        self.pub_pem = self.pub.save_pkcs1("PEM").decode('utf-8')

    def handshake(self, ip: str, agent_pub_pem: str, password: str) -> bool:
        """Проводит Handshake с Агентом."""
        agent_pub = rsa.PublicKey.load_pkcs1(agent_pub_pem.encode('utf-8'))
        pub_hash = hashlib.sha256(self.pub_pem.encode('utf-8')).hexdigest()
        
        # Пакуем пароль и хэш
        auth_data = json.dumps({"p": password, "h": pub_hash})
        encrypted_auth = rsa.encrypt(auth_data.encode('utf-8'), agent_pub)
        auth_payload_b64 = base64.b64encode(encrypted_auth).decode('utf-8')

        msg = {
            "action": "handshake",
            "orchestrator_pub_key": self.pub_pem,
            "auth_payload": auth_payload_b64
        }
        
        resp = self._send_tcp(ip, 50001, msg)
        if not resp:
            return False
            
        if "encrypted_payload" in resp:
            enc_bytes = base64.b64decode(resp["encrypted_payload"])
            try:
                dec = rsa.decrypt(enc_bytes, self.priv).decode('utf-8')
                data = json.loads(dec)
                return data.get("status") == "ok"
            except Exception:
                return False
        return False

    def send_command(self, ip: str, agent_pub_pem: str, command: str) -> dict:
        """Отправляет зашифрованную терминальную команду."""
        cmd_data = {
            "action": "terminal_cmd",
            "cmd": command,
            "orchestrator_pub_key": self.pub_pem
        }
        return self._send_encrypted_payload(ip, agent_pub_pem, cmd_data)

    def send_text(self, ip: str, agent_pub_pem: str, text: str) -> dict:
        """Отправляет обычный текст (эхо)."""
        cmd_data = {
            "action": "echo",
            "text": text,
            "orchestrator_pub_key": self.pub_pem
        }
        return self._send_encrypted_payload(ip, agent_pub_pem, cmd_data)

    def _send_encrypted_payload(self, ip: str, agent_pub_pem: str, cmd_data: dict) -> dict:
        agent_pub = rsa.PublicKey.load_pkcs1(agent_pub_pem.encode('utf-8'))
        
        # Шифрование чанками
        data_str = json.dumps(cmd_data).encode('utf-8')
        chunks = [data_str[i:i+200] for i in range(0, len(data_str), 200)]
        enc_chunks = [rsa.encrypt(c, agent_pub) for c in chunks]
        enc_b64 = base64.b64encode(b"".join(enc_chunks)).decode('utf-8')
        
        msg = {
            "encrypted_command": enc_b64
        }
        
        resp = self._send_tcp(ip, 50001, msg)
        if not resp:
            return {"status": "error", "error": "No response or connection failed"}
            
        if "encrypted_payload" in resp:
            enc_resp_bytes = base64.b64decode(resp["encrypted_payload"])
            # Расшифровка чанками
            resp_chunks = [enc_resp_bytes[i:i+256] for i in range(0, len(enc_resp_bytes), 256)]
            try:
                dec_chunks = [rsa.decrypt(c, self.priv) for c in resp_chunks]
                return json.loads(b"".join(dec_chunks).decode('utf-8'))
            except Exception as e:
                return {"status": "error", "error": f"Decrypt error: {e}"}
        
        return resp

    def _send_tcp(self, ip: str, port: int, msg_dict: dict):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            s.sendall(json.dumps(msg_dict).encode('utf-8'))
            data = s.recv(4096).decode('utf-8')
            s.close()
            if data:
                return json.loads(data)
        except Exception:
            return None
