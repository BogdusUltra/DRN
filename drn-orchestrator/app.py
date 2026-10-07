import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
import threading
import socket
import json
import time
from client import DRNClient

class DRNStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DRN Studio (Test UI)")
        self.root.geometry("800x500")
        
        self.nodes = {}  # ip -> {"name": str, "pubkey": str, "last_seen": float, "auth": bool}
        self.client = None
        self.password = ""
        
        self.setup_ui()
        
        # Start UDP listener
        self.running = True
        threading.Thread(target=self.udp_listener, daemon=True).start()
        threading.Thread(target=self.update_status_loop, daemon=True).start()

    def setup_ui(self):
        # Top Frame (Password & Actions)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(top_frame, text="Password:").pack(side=tk.LEFT)
        self.pass_entry = tk.Entry(top_frame, show="*", width=20)
        self.pass_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="Set Password", command=self.set_password).pack(side=tk.LEFT)
        tk.Button(top_frame, text="Handshake Selected", command=self.do_handshake).pack(side=tk.LEFT, padx=10)
        tk.Button(top_frame, text="Delete Selected", command=self.delete_node).pack(side=tk.LEFT)

        # Main Frame (List & Terminal)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Node List
        list_frame = tk.Frame(main_frame, width=250)
        list_frame.pack(side=tk.LEFT, fill=tk.Y)
        list_frame.pack_propagate(False)
        
        tk.Label(list_frame, text="Machines (IP : Name)").pack(anchor=tk.W)
        self.tree = ttk.Treeview(list_frame, columns=("ip", "name", "status"), show="headings")
        self.tree.heading("ip", text="IP")
        self.tree.heading("name", text="Name")
        self.tree.heading("status", text="Status")
        self.tree.column("ip", width=100)
        self.tree.column("name", width=80)
        self.tree.column("status", width=60)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.tree.tag_configure("online", foreground="green")
        self.tree.tag_configure("auth", foreground="blue")
        self.tree.tag_configure("offline_3s", foreground="gray")
        self.tree.tag_configure("offline_auth", foreground="#A9A9A9") # light gray / dimmed
        
        # Right: Terminal
        term_frame = tk.Frame(main_frame)
        term_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(term_frame, text="Terminal").pack(anchor=tk.W)
        self.terminal = scrolledtext.ScrolledText(term_frame, state='disabled', bg="black", fg="white", font=("Courier", 12))
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        cmd_frame = tk.Frame(term_frame)
        cmd_frame.pack(fill=tk.X, pady=5)
        self.cmd_entry = tk.Entry(cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", self.send_command)
        tk.Button(cmd_frame, text="Send", command=self.send_command).pack(side=tk.LEFT, padx=5)

    def log(self, msg):
        self.terminal.config(state='normal')
        self.terminal.insert(tk.END, msg + "\n")
        self.terminal.see(tk.END)
        self.terminal.config(state='disabled')

    def set_password(self):
        self.password = self.pass_entry.get()
        self.client = DRNClient(self.password)
        self.log(f"[*] Password set. Ready for Handshake.")

    def udp_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 50000))
        
        while self.running:
            try:
                data, addr = s.recvfrom(4096)
                msg = json.loads(data.decode('utf-8'))
                if msg.get("action") == "beacon":
                    ip = addr[0]
                    name = msg.get("name")
                    pubkey = msg.get("public_key")
                    
                    if ip not in self.nodes:
                        self.nodes[ip] = {"name": name, "pubkey": pubkey, "last_seen": time.time(), "auth": False}
                        self.log(f"[+] Discovered new agent: {name} ({ip})")
                        self.refresh_list()
                    else:
                        self.nodes[ip]["last_seen"] = time.time()
            except Exception:
                pass

    def update_status_loop(self):
        while self.running:
            time.sleep(1)
            self.refresh_list()

    def refresh_list(self):
        # Clean existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        now = time.time()
        to_delete = []
        
        for ip, data in self.nodes.items():
            age = now - data["last_seen"]
            status_text = "Online"
            tag = "online"
            
            if data["auth"]:
                if age > 10:
                    status_text = "Off(Auth)"
                    tag = "offline_auth"
                elif age > 3:
                    status_text = "Lag(Auth)"
                    tag = "offline_auth"
                else:
                    status_text = "Auth"
                    tag = "auth"
            else:
                if age > 10:
                    to_delete.append(ip)
                    continue
                elif age > 3:
                    status_text = "Offline"
                    tag = "offline_3s"
            
            self.tree.insert("", "end", iid=ip, values=(ip, data["name"], status_text), tags=(tag,))
            
        for ip in to_delete:
            del self.nodes[ip]
            self.log(f"[-] Removed inactive unauth agent: {ip}")

    def get_selected_ip(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a machine first.")
            return None
        return sel[0]

    def do_handshake(self):
        ip = self.get_selected_ip()
        if not ip: return
        
        if not self.client:
            messagebox.showwarning("Warning", "Please set the password first.")
            return
            
        data = self.nodes[ip]
        self.log(f"[*] Initiating Handshake with {ip}...")
        
        def task():
            success = self.client.handshake(ip, data["pubkey"])
            if success:
                self.nodes[ip]["auth"] = True
                self.log(f"[+] Handshake SUCCESS with {ip}!")
            else:
                self.log(f"[-] Handshake FAILED with {ip}.")
            self.refresh_list()
            
        threading.Thread(target=task, daemon=True).start()

    def delete_node(self):
        ip = self.get_selected_ip()
        if not ip: return
        del self.nodes[ip]
        self.refresh_list()
        self.log(f"[*] Manually deleted {ip} from list.")

    def send_command(self, event=None):
        ip = self.get_selected_ip()
        if not ip: return
        
        cmd = self.cmd_entry.get()
        if not cmd: return
        self.cmd_entry.delete(0, tk.END)
        
        if not self.nodes[ip]["auth"]:
            self.log("[-] Agent is not authorized! Do handshake first.")
            return
            
        self.log(f"> {cmd} (to {ip})")
        def task():
            resp = self.client.send_command(ip, self.nodes[ip]["pubkey"], cmd)
            if "error" in resp:
                self.log(f"[-] Error: {resp['error']}")
            else:
                if resp.get("stdout"):
                    self.log(resp["stdout"].strip())
                if resp.get("stderr"):
                    self.log(f"[!] STDERR: {resp['stderr'].strip()}")
                self.log(f"[+] Return code: {resp.get('returncode')}")
                
        threading.Thread(target=task, daemon=True).start()

def main():
    root = tk.Tk()
    app = DRNStudioApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
