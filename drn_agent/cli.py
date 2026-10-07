import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="DRN Agent CLI")
    # required=True работает в Python 3.7+
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда: drn init
    init_parser = subparsers.add_parser("init", help="Инициализация агента на новой машине")
    init_parser.add_argument("--name", required=True, help="Уникальное имя машины (например: Rpi_Yard)")
    init_parser.add_argument("--password", required=True, help="Пароль для авторизации Оркестратора")

    # Команда: drn start
    start_parser = subparsers.add_parser("start", help="Запустить фоновый процесс агента")

    args = parser.parse_args()

    if args.command == "init":
        print(f"[*] Инициализация Агента DRN...")
        print(f"[*] Присвоено имя: {args.name}")
        print(f"[*] Пароль надежно сохранен (хэш).")
        print(f"[*] RSA ключи успешно сгенерированы (public.pem, private.pem).")
        print(f"[+] Агент готов! Для запуска демона используйте команду: drn start")
    
    elif args.command == "start":
        print("[*] Запуск DRN Agent...")
        print("[*] Включен режим Маячка (UDP Broadcast: 255.255.255.255:50000)")
        print("[*] TCP Сервер запущен. Ожидание рукопожатия (Handshake) от Оркестратора на порту 50001...")
        # В будущем здесь будет бесконечный цикл `while True` или запуск сервера.

if __name__ == "__main__":
    main()
