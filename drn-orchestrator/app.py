import sys
import socket
import json
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTreeWidget, QTreeWidgetItem, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from client import DRNClient

class UDPListenerThread(QThread):
    node_discovered = pyqtSignal(str, str, str) # ip, name, pubkey

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
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
                    self.node_discovered.emit(ip, name, pubkey)
            except Exception:
                pass

    def stop(self):
        self.running = False

class HandshakeThread(QThread):
    finished = pyqtSignal(str, bool)

    def __init__(self, client, ip, pubkey):
        super().__init__()
        self.client = client
        self.ip = ip
        self.pubkey = pubkey

    def run(self):
        success = self.client.handshake(self.ip, self.pubkey)
        self.finished.emit(self.ip, success)

class CommandThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, client, ip, pubkey, command):
        super().__init__()
        self.client = client
        self.ip = ip
        self.pubkey = pubkey
        self.command = command

    def run(self):
        resp = self.client.send_command(self.ip, self.pubkey, self.command)
        self.finished.emit(resp)

class DRNStudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DRN Studio (PyQt6)")
        self.resize(900, 600)
        
        self.nodes = {}
        self.client = None
        
        self.setup_ui()
        
        self.udp_thread = UDPListenerThread()
        self.udp_thread.node_discovered.connect(self.on_node_discovered)
        self.udp_thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_list)
        self.timer.start(1000)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top Bar
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Password:"))
        self.pass_entry = QLineEdit()
        self.pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        top_layout.addWidget(self.pass_entry)
        
        btn_set_pass = QPushButton("Set Password")
        btn_set_pass.clicked.connect(self.set_password)
        top_layout.addWidget(btn_set_pass)

        btn_hs = QPushButton("Handshake Selected")
        btn_hs.clicked.connect(self.do_handshake)
        top_layout.addWidget(btn_hs)

        btn_del = QPushButton("Delete Selected")
        btn_del.clicked.connect(self.delete_node)
        top_layout.addWidget(btn_del)
        
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Splitter Layout
        split_layout = QHBoxLayout()
        
        # Left Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["IP", "Name", "Status"])
        self.tree.setColumnWidth(0, 140)
        self.tree.setColumnWidth(1, 100)
        split_layout.addWidget(self.tree, 1)

        # Right Terminal
        term_layout = QVBoxLayout()
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: black; color: #00FF00; font-family: monospace; font-size: 13px;")
        term_layout.addWidget(self.terminal)

        cmd_layout = QHBoxLayout()
        self.cmd_entry = QLineEdit()
        self.cmd_entry.returnPressed.connect(self.send_command)
        cmd_layout.addWidget(self.cmd_entry)
        
        btn_send = QPushButton("Send")
        btn_send.clicked.connect(self.send_command)
        cmd_layout.addWidget(btn_send)
        
        term_layout.addLayout(cmd_layout)
        split_layout.addLayout(term_layout, 2)
        
        main_layout.addLayout(split_layout)

    def log(self, msg):
        self.terminal.append(msg)
        # Scroll to bottom
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_password(self):
        password = self.pass_entry.text()
        if not password: return
        self.client = DRNClient(password)
        self.log("[*] Password set. Ready for Handshake.")

    def on_node_discovered(self, ip, name, pubkey):
        if ip not in self.nodes:
            self.nodes[ip] = {"name": name, "pubkey": pubkey, "last_seen": time.time(), "auth": False, "item": None}
            self.log(f"[+] Discovered new agent: {name} ({ip})")
            self.refresh_list()
        else:
            self.nodes[ip]["last_seen"] = time.time()

    def refresh_list(self):
        now = time.time()
        to_delete = []
        
        for ip, data in self.nodes.items():
            age = now - data["last_seen"]
            status_text = "Online"
            color = QColor("#00FF00") # Green
            
            if data["auth"]:
                if age > 10:
                    status_text = "Off(Auth)"
                    color = QColor("#808080") # Gray
                elif age > 3:
                    status_text = "Lag(Auth)"
                    color = QColor("#A9A9A9")
                else:
                    status_text = "Auth"
                    color = QColor("#00BFFF") # DeepSkyBlue
            else:
                if age > 10:
                    to_delete.append(ip)
                    continue
                elif age > 3:
                    status_text = "Offline"
                    color = QColor("#808080")

            item = data["item"]
            if not item:
                item = QTreeWidgetItem(self.tree, [ip, data["name"], status_text])
                data["item"] = item
            else:
                item.setText(2, status_text)
            
            item.setForeground(0, color)
            item.setForeground(1, color)
            item.setForeground(2, color)

        for ip in to_delete:
            item = self.nodes[ip]["item"]
            if item:
                index = self.tree.indexOfTopLevelItem(item)
                self.tree.takeTopLevelItem(index)
            del self.nodes[ip]
            self.log(f"[-] Removed inactive unauth agent: {ip}")

    def get_selected_ip(self):
        sel = self.tree.selectedItems()
        if not sel:
            QMessageBox.warning(self, "Warning", "Please select a machine first.")
            return None
        return sel[0].text(0)

    def do_handshake(self):
        ip = self.get_selected_ip()
        if not ip: return
        if not self.client:
            QMessageBox.warning(self, "Warning", "Please set the password first.")
            return
            
        data = self.nodes[ip]
        self.log(f"[*] Initiating Handshake with {ip}...")
        
        self.hs_thread = HandshakeThread(self.client, ip, data["pubkey"])
        self.hs_thread.finished.connect(self.on_handshake_finished)
        self.hs_thread.start()

    def on_handshake_finished(self, ip, success):
        if success:
            if ip in self.nodes:
                self.nodes[ip]["auth"] = True
            self.log(f"[+] Handshake SUCCESS with {ip}!")
        else:
            self.log(f"[-] Handshake FAILED with {ip}.")
        self.refresh_list()

    def delete_node(self):
        ip = self.get_selected_ip()
        if not ip: return
        item = self.nodes[ip]["item"]
        if item:
            index = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(index)
        del self.nodes[ip]
        self.log(f"[*] Manually deleted {ip} from list.")

    def send_command(self):
        ip = self.get_selected_ip()
        if not ip: return
        
        cmd = self.cmd_entry.text()
        if not cmd: return
        self.cmd_entry.clear()
        
        if not self.nodes[ip]["auth"]:
            self.log("[-] Agent is not authorized! Do handshake first.")
            return
            
        self.log(f"\n> {cmd} (to {ip})")
        
        self.cmd_thread = CommandThread(self.client, ip, self.nodes[ip]["pubkey"], cmd)
        self.cmd_thread.finished.connect(self.on_command_finished)
        self.cmd_thread.start()

    def on_command_finished(self, resp):
        if "error" in resp:
            self.log(f"[-] Error: {resp['error']}")
        else:
            if resp.get("stdout"):
                self.log(resp["stdout"].strip())
            if resp.get("stderr"):
                self.log(f"<span style='color:red'>[!] STDERR: {resp['stderr'].strip()}</span>")
            self.log(f"[+] Return code: {resp.get('returncode')}")

    def closeEvent(self, event):
        self.udp_thread.stop()
        self.udp_thread.wait()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = DRNStudioApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
