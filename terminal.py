import tkinter as tk
from tkinter import scrolledtext, messagebox
import paramiko
import threading
import sys
import re
import time
import argparse

class TerminalWindow(tk.Tk):
    def __init__(self, ip, port, user, password, theme_mode="dark", command=None):
        super().__init__()
        self.title(f"SSH Terminal: {user}@{ip}")
        self.geometry("800x600")
        
        self.ip = ip
        self.port = int(port)
        self.user = user
        self.password = password
        self.command = command
        
        # Theme
        if theme_mode == "dark":
            self.bg_color = "#202020"
            self.fg_color = "#ffffff"
        else:
            self.bg_color = "#f3f3f3"
            self.fg_color = "#1a1a1a"
            
        self.configure(bg=self.bg_color)
        
        # Text area
        self.text_area = scrolledtext.ScrolledText(self, state='disabled', 
                                                 bg=self.bg_color, fg=self.fg_color, 
                                                 font=("Consolas", 10), 
                                                 insertbackground=self.fg_color)
        self.text_area.pack(expand=True, fill='both')
        
        # Bindings
        self.text_area.bind("<Key>", self.on_key)
        self.text_area.bind("<Return>", self.on_enter)
        self.text_area.bind("<BackSpace>", self.on_backspace)
        
        self.running = True
        self.client = None
        self.channel = None
        
        # Start connection
        self.connect_thread = threading.Thread(target=self.connect_ssh, daemon=True)
        self.connect_thread.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def connect_ssh(self):
        try:
            self.update_terminal(f"Connecting to {self.user}@{self.ip}...\n")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.ip, port=self.port, username=self.user, password=self.password)
            
            self.channel = self.client.invoke_shell()
            self.update_terminal("Connected.\n")
            
            if self.command:
                self.update_terminal(f"Executing: {self.command}\n")
                self.channel.send(self.command + "\n")
            
            # Start receiving
            self.recv_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.recv_thread.start()
            
        except Exception as e:
            self.update_terminal(f"Connection failed: {str(e)}\n")

    def on_key(self, event):
        if not self.channel: return
        if len(event.char) > 0 and ord(event.char) >= 32:
            self.channel.send(event.char)
            return "break"

    def on_enter(self, event):
        if not self.channel: return
        self.channel.send("\n")
        return "break"

    def on_backspace(self, event):
        if not self.channel: return
        self.channel.send("\x7f")
        return "break"

    def receive_data(self):
        while self.running and self.channel:
            if self.channel.recv_ready():
                try:
                    data = self.channel.recv(1024).decode('utf-8', errors='ignore')
                    if not data: break
                    clean_data = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', data) 
                    self.after(0, self.update_terminal, clean_data)
                except:
                    break
            time.sleep(0.01)

    def update_terminal(self, data):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, data)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def on_close(self):
        self.running = False
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-u", "--user", required=True)
    parser.add_argument("-h", "--host", required=True)
    parser.add_argument("-p", "--port", default="22")
    parser.add_argument("-pwd", "--password", required=True)
    parser.add_argument("-t", "--theme", default="dark")
    parser.add_argument("-cmd", "--command", help="Initial command to run")
    
    args = parser.parse_args()
    
    app = TerminalWindow(args.host, args.port, args.user, args.password, args.theme, args.command)
    app.mainloop()
