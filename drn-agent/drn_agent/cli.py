import argparse
import sys
import os
import json
import subprocess
import signal
import shutil
from .crypto import generate_keys, hash_password
from .server import start_agent_daemon

def stop_daemon(pid_file):
    """Останавливает фоновый процесс, если он запущен."""
    if not os.path.exists(pid_file):
        return False
    with open(pid_file, "r") as f:
        try:
            pid = int(f.read())
        except ValueError:
            os.remove(pid_file)
            return False
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"[*] Фоновый процесс (PID: {pid}) остановлен.")
    except ProcessLookupError:
        pass # Процесс уже мертв
    
    if os.path.exists(pid_file):
        os.remove(pid_file)
    return True

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
    
    # drn reset
    reset_parser = subparsers.add_parser("reset", help="Полностью удалить все данные и ключи агента")

    # скрытая команда
    hidden_parser = subparsers.add_parser("_run_server", help=argparse.SUPPRESS)

    args = parser.parse_args()

    home_dir = os.path.expanduser("~")
    drn_dir = os.path.join(home_dir, ".drn_agent")
    pid_file = os.path.join(drn_dir, "agent.pid")

    if args.command == "init":
        # Защита от перезаписи
        if os.path.exists(os.path.join(drn_dir, "config.json")):
            print("[!] Внимание: Агент уже инициализирован на этой машине.")
            ans = input("    Хотите перезаписать все данные и ключи? (y/N): ")
            if ans.lower() != 'y':
                print("[-] Операция отменена.")
                return
            # Останавливаем демона перед генерацией новых ключей
            stop_daemon(pid_file)

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
        subprocess.Popen([sys.argv[0], "_run_server"],
                         start_new_session=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        print("[+] Агент успешно запущен в фоне. Терминал свободен.")

    elif args.command == "stop":
        if not stop_daemon(pid_file):
            print("[-] Агент не запущен (PID-файл не найден).")
        else:
            print("[+] Остановка завершена.")

    elif args.command == "reset":
        if not os.path.exists(drn_dir):
            print("[-] Папка агента не найдена. Удалять нечего.")
            return
        
        print("[!] Внимание: Это действие безвозвратно удалит все RSA ключи,")
        print("    хэши паролей и белый список Оркестраторов.")
        ans = input("    Вы уверены, что хотите полностью сбросить машину? (y/N): ")
        
        if ans.lower() == 'y':
            stop_daemon(pid_file)
            shutil.rmtree(drn_dir)
            print("[+] Все данные Агента успешно удалены с этой машины.")
        else:
            print("[-] Операция отменена.")

    elif args.command == "_run_server":
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        try:
            start_agent_daemon(drn_dir)
        finally:
            if os.path.exists(pid_file):
                os.remove(pid_file)

if __name__ == "__main__":
    main()
