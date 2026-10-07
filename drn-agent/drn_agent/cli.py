import argparse
import sys
import os
import json
from .crypto import generate_keys, hash_password
from .server import start_agent_daemon

def main():
    parser = argparse.ArgumentParser(description="DRN Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда: drn init
    init_parser = subparsers.add_parser("init", help="Инициализация агента на новой машине")
    init_parser.add_argument("--name", required=True, help="Уникальное имя машины (например: Rpi_Yard)")
    init_parser.add_argument("--password", required=True, help="Пароль для авторизации Оркестратора")

    # Команда: drn start
    start_parser = subparsers.add_parser("start", help="Запустить фоновый процесс агента")

    args = parser.parse_args()

    if args.command == "init":
        home_dir = os.path.expanduser("~")
        drn_dir = os.path.join(home_dir, ".drn_agent")
        os.makedirs(drn_dir, exist_ok=True)
        
        print(f"[*] Генерация RSA ключей (2048 бит) в директории {drn_dir}...")
        generate_keys(drn_dir)
        
        config_data = {
            "name": args.name,
            "password_hash": hash_password(args.password),
            "whitelist": []
        }
        
        with open(os.path.join(drn_dir, "config.json"), "w") as f:
            json.dump(config_data, f, indent=4)
            
        print(f"[+] Инициализация успешно завершена!")
        print(f"[+] Машина: {args.name}")
        print(f"[+] Агент готов! Для запуска демона используйте команду: drn start")
    
    elif args.command == "start":
        print("[*] Запуск DRN Agent...")
        start_agent_daemon()

if __name__ == "__main__":
    main()
