import argparse
import sys
import os
import json
import subprocess
import signal
from .crypto import generate_keys, hash_password
from .server import start_agent_daemon

def main():
    parser = argparse.ArgumentParser(description="DRN Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # drn init
    init_parser = subparsers.add_parser("init", help="Инициализация агента на новой машине")
    init_parser.add_argument("--name", required=True, help="Уникальное имя машины")
    init_parser.add_argument("--password", required=True, help="Пароль для авторизации Оркестратора")

    # drn start
    start_parser = subparsers.add_parser("start", help="Запустить процесс агента в фоновом режиме")

    # drn stop
    stop_parser = subparsers.add_parser("stop", help="Остановить фоновый процесс агента")

    # Скрытая команда для запуска демона под капотом
    hidden_parser = subparsers.add_parser("_run_server", help=argparse.SUPPRESS)

    args = parser.parse_args()

    home_dir = os.path.expanduser("~")
    drn_dir = os.path.join(home_dir, ".drn_agent")
    pid_file = os.path.join(drn_dir, "agent.pid")

    if args.command == "init":
        os.makedirs(drn_dir, exist_ok=True)
        print(f"[*] Генерация RSA ключей в {drn_dir}...")
        generate_keys(drn_dir)
        
        config_data = {
            "name": args.name,
            "password_hash": hash_password(args.password),
            "whitelist": []
        }
        
        with open(os.path.join(drn_dir, "config.json"), "w") as f:
            json.dump(config_data, f, indent=4)
            
        print(f"[+] Инициализация успешно завершена! Машина: {args.name}")
    
    elif args.command == "start":
        if os.path.exists(pid_file):
            print("[-] Агент уже запущен! Если это ошибка, выполните 'drn stop'.")
            return
        
        print("[*] Отправка агента в фоновый режим (Daemonize)...")
        # sys.argv[0] хранит путь к команде 'drn'
        subprocess.Popen([sys.argv[0], "_run_server"],
                         start_new_session=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        print("[+] Агент успешно запущен в фоне. Терминал свободен.")

    elif args.command == "stop":
        if not os.path.exists(pid_file):
            print("[-] Агент не запущен (PID-файл не найден).")
            return
        
        with open(pid_file, "r") as f:
            pid = int(f.read())
        
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[+] Процесс агента (PID: {pid}) успешно остановлен.")
        except ProcessLookupError:
            print("[-] Процесс не найден, возможно он был завершен ранее.")
        
        if os.path.exists(pid_file):
            os.remove(pid_file)

    elif args.command == "_run_server":
        # Логика самого фонового демона
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        
        try:
            start_agent_daemon(drn_dir)
        finally:
            if os.path.exists(pid_file):
                os.remove(pid_file)

if __name__ == "__main__":
    main()
