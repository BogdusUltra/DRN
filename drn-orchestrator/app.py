import curses
import threading
import socket
import json
import time
from client import DRNClient

# Shared state
nodes = {}
running = True
log_messages = []
client = None

def main(stdscr):
    global running, nodes, log_messages, client
    
    curses.curs_set(0) # Hide cursor initially
    stdscr.nodelay(True)
    stdscr.timeout(500)
    
    password = ""
    client = None
    nodes = {}
    log_messages = []
    running = True
    
    def log(msg):
        log_messages.append(msg)
        if len(log_messages) > 15:
            log_messages.pop(0)

    # Start UDP thread
    def udp_listener():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 50000))
        while running:
            try:
                data, addr = s.recvfrom(4096)
                msg = json.loads(data.decode('utf-8'))
                if msg.get("action") == "beacon":
                    ip = addr[0]
                    name = msg.get("name")
                    pubkey = msg.get("public_key")
                    if ip not in nodes:
                        nodes[ip] = {"name": name, "pubkey": pubkey, "last_seen": time.time(), "auth": False}
                        log(f"[+] Discovered: {name} ({ip})")
                    else:
                        nodes[ip]["last_seen"] = time.time()
            except Exception:
                pass

    threading.Thread(target=udp_listener, daemon=True).start()
    
    # Prompt for password
    stdscr.clear()
    stdscr.addstr(0, 0, "Enter Orchestrator Password (hit Enter): ")
    stdscr.refresh()
    curses.curs_set(1)
    stdscr.nodelay(False)
    curses.echo()
    password = stdscr.getstr(0, 41, 20).decode('utf-8')
    curses.noecho()
    stdscr.nodelay(True)
    curses.curs_set(0)
    
    client = DRNClient(password)
    log("[*] Password set. Listening for beacons...")
    
    selected_idx = 0
    mode = "normal"
    input_str = ""
    
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    
    while running:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # Draw Top Bar
        stdscr.addstr(0, 0, f"DRN Studio (Terminal) - Password: {'*' * len(password)}", curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * w)
        
        # Cleanup nodes
        now = time.time()
        to_delete = []
        node_list = []
        for ip, data in list(nodes.items()):
            age = now - data["last_seen"]
            if data["auth"]:
                if age > 10: status = "Off(Auth)"
                elif age > 3: status = "Lag(Auth)"
                else: status = "Auth"
            else:
                if age > 10:
                    to_delete.append(ip)
                    continue
                elif age > 3: status = "Offline"
                else: status = "Online"
            node_list.append({"ip": ip, "name": data["name"], "status": status, "auth": data["auth"]})
            
        for ip in to_delete:
            del nodes[ip]
            log(f"[-] Removed inactive unauth: {ip}")
            
        # Ensure selection is valid
        if selected_idx >= len(node_list):
            selected_idx = max(0, len(node_list) - 1)
            
        # Draw Nodes List
        stdscr.addstr(2, 0, "Machines:", curses.A_BOLD)
        for i, n in enumerate(node_list):
            prefix = "-> " if i == selected_idx else "   "
            color = curses.color_pair(1) if n["status"] == "Online" else curses.color_pair(2) if n["auth"] else curses.color_pair(3)
            stdscr.addstr(3+i, 0, f"{prefix}{n['name']} ({n['ip']}) - [{n['status']}]", color)
            
        # Draw Terminal Log (Bottom)
        log_start_y = max(4 + len(node_list), h - 18)
        stdscr.addstr(log_start_y, 0, "-" * w)
        stdscr.addstr(log_start_y+1, 0, "Terminal Log:")
        for i, m in enumerate(log_messages):
            if log_start_y + 2 + i < h - 2:
                stdscr.addstr(log_start_y + 2 + i, 0, m[:w-1])
                
        # Draw Input Area
        stdscr.addstr(h-2, 0, "-" * w)
        if mode == "normal":
            stdscr.addstr(h-1, 0, "[UP/DOWN] Select | [H] Handshake | [C] Send Command | [D] Delete | [Q] Quit")
            curses.curs_set(0)
        elif mode == "cmd":
            stdscr.addstr(h-1, 0, f"Command: {input_str}")
            curses.curs_set(1)
            
        stdscr.refresh()
        
        # Handle input
        try:
            c = stdscr.getch()
        except Exception:
            continue
            
        if c == -1:
            continue
            
        if mode == "normal":
            if c in (ord('q'), ord('Q')):
                running = False
            elif c == curses.KEY_UP and selected_idx > 0:
                selected_idx -= 1
            elif c == curses.KEY_DOWN and selected_idx < len(node_list) - 1:
                selected_idx += 1
            elif c in (ord('h'), ord('H')):
                if node_list:
                    ip = node_list[selected_idx]['ip']
                    def do_hs(target_ip, target_pub):
                        log(f"[*] Handshake with {target_ip}...")
                        if client.handshake(target_ip, target_pub):
                            nodes[target_ip]["auth"] = True
                            log(f"[+] Handshake SUCCESS with {target_ip}")
                        else:
                            log(f"[-] Handshake FAILED with {target_ip}")
                    threading.Thread(target=do_hs, args=(ip, nodes[ip]["pubkey"]), daemon=True).start()
            elif c in (ord('d'), ord('D')):
                if node_list:
                    ip = node_list[selected_idx]['ip']
                    del nodes[ip]
            elif c in (ord('c'), ord('C')):
                if node_list:
                    if not node_list[selected_idx]["auth"]:
                        log("[-] Agent not auth! Do handshake first.")
                    else:
                        mode = "cmd"
                        input_str = ""
        elif mode == "cmd":
            if c in (10, 13): # Enter
                if input_str:
                    ip = node_list[selected_idx]['ip']
                    cmd_to_send = input_str
                    log(f"> {cmd_to_send}")
                    def do_cmd(target_ip, target_pub, command):
                        resp = client.send_command(target_ip, target_pub, command)
                        if "error" in resp: log(f"[-] Err: {resp['error']}")
                        else:
                            if resp.get("stdout"):
                                for line in resp["stdout"].strip().split("\n"): log(line)
                            if resp.get("stderr"):
                                for line in resp["stderr"].strip().split("\n"): log(f"[!] {line}")
                            log(f"[+] Code: {resp.get('returncode')}")
                    threading.Thread(target=do_cmd, args=(ip, nodes[ip]["pubkey"], cmd_to_send), daemon=True).start()
                mode = "normal"
            elif c == 27: # Esc
                mode = "normal"
            elif c in (curses.KEY_BACKSPACE, 127, 8):
                input_str = input_str[:-1]
            else:
                if 32 <= c <= 126:
                    input_str += chr(c)

if __name__ == "__main__":
    curses.wrapper(main)
