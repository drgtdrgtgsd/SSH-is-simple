import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import paramiko
import threading
import socket
import sys
import re
import select
import time

class TerminalWindow(tk.Toplevel):
    def __init__(self, master, client, channel, title="SSH Terminal", bg_color="black", fg_color="white"):
        super().__init__(master)
        self.title(title)
        self.geometry("800x600")
        self.client = client
        self.channel = channel
        self.running = True
        self.bg_color = bg_color
        self.fg_color = fg_color

        # Text area for terminal output
        self.text_area = scrolledtext.ScrolledText(self, state='disabled', bg=self.bg_color, fg=self.fg_color, font=("Consolas", 10), insertbackground=self.fg_color)
        self.text_area.pack(expand=True, fill='both')
        
        # Bind key events
        self.text_area.bind("<Key>", self.on_key)
        self.text_area.bind("<Return>", self.on_enter)
        self.text_area.bind("<BackSpace>", self.on_backspace)
        
        # Start receiving thread
        self.recv_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.recv_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_key(self, event):
        if len(event.char) > 0 and ord(event.char) >= 32:
            self.channel.send(event.char)
            return "break"

    def on_enter(self, event):
        self.channel.send("\n")
        return "break"

    def on_backspace(self, event):
        self.channel.send("\x7f")
        return "break"

    def receive_data(self):
        while self.running:
            if self.channel.recv_ready():
                try:
                    data = self.channel.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        break
                    clean_data = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', data) 
                    
                    # Schedule GUI update on main thread
                    self.after(0, self.update_terminal, clean_data)
                except Exception:
                    break
            time.sleep(0.01)

    def update_terminal(self, data):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, data)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def on_close(self):
        self.running = False
        try:
            self.channel.close()
            self.client.close()
        except:
            pass
        self.destroy()

class PortForwarder(threading.Thread):
    def __init__(self, local_port, remote_host, remote_port, transport):
        super().__init__(daemon=True)
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.transport = transport
        self.server_socket = None
        self.running = True

    def run(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.local_port))
            self.server_socket.listen(5)
            print(f"Forwarding localhost:{self.local_port} -> {self.remote_host}:{self.remote_port}")
            
            while self.running:
                client_socket, addr = self.server_socket.accept()
                if not self.running:
                    break
                threading.Thread(target=self.handle_connection, args=(client_socket,), daemon=True).start()
        except Exception as e:
            print(f"Port forwarding failed on {self.local_port}: {e}")

    def handle_connection(self, client_socket):
        try:
            channel = self.transport.open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                client_socket.getpeername()
            )
            if channel is None:
                client_socket.close()
                return

            while True:
                r, w, x = select.select([client_socket, channel], [], [])
                if client_socket in r:
                    data = client_socket.recv(1024)
                    if len(data) == 0: break
                    channel.send(data)
                if channel in r:
                    data = channel.recv(1024)
                    if len(data) == 0: break
                    client_socket.send(data)
            
            channel.close()
            client_socket.close()
        except Exception as e:
            try:
                client_socket.close()
            except:
                pass

class PortMappingRow(ttk.Frame):
    def __init__(self, parent, app, index):
        super().__init__(parent)
        self.app = app
        self.index = index
        
        # Widgets
        self.local_port = self.app.create_themed_entry(self, width=10)
        self.remote_host = self.app.create_themed_entry(self, width=15)
        self.remote_port = self.app.create_themed_entry(self, width=10)
        self.remove_btn = ttk.Button(self, text="-", width=3, command=self.remove)
        
        # Layout
        ttk.Label(self, text="本地:").pack(side=tk.LEFT, padx=2)
        self.local_port.pack(side=tk.LEFT, padx=2)
        ttk.Label(self, text="远程IP:").pack(side=tk.LEFT, padx=2)
        self.remote_host.pack(side=tk.LEFT, padx=2)
        ttk.Label(self, text="远程端口:").pack(side=tk.LEFT, padx=2)
        self.remote_port.pack(side=tk.LEFT, padx=2)
        self.remove_btn.pack(side=tk.LEFT, padx=5)
        
        self.pack(fill=tk.X, pady=2)

    def remove(self):
        self.app.remove_mapping_row(self)

class HoverButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.default_bg = kwargs.get('bg', 'white')
        self.hover_bg = kwargs.pop('hover_bg', '#e5e5e5')
        self.default_fg = kwargs.get('fg', 'black')
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['bg'] = self.hover_bg

    def on_leave(self, e):
        self['bg'] = self.default_bg

class SSHGui:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Simple GUI - by 高粱NexT")
        self.root.geometry("500x700")
        self.root.resizable(True, True)
        
        # Fade In Effect
        self.root.attributes('-alpha', 0.0)
        self.fade_in()

        # --- Theme Setup ---
        self.is_dark = False
        self.themes = {
            "dark": {
                "bg": "#202020", "fg": "#ffffff",
                "entry_bg": "#2d2d2d", "entry_fg": "#ffffff",
                "btn_bg": "#333333", "btn_hover": "#404040", "btn_fg": "#ffffff",
                "disabled_bg": "#202020", "disabled_fg": "#666666"
            },
            "light": {
                "bg": "#f3f3f3", "fg": "#1a1a1a",
                "entry_bg": "#ffffff", "entry_fg": "#1a1a1a",
                "btn_bg": "#ffffff", "btn_hover": "#e5e5e5", "btn_fg": "#1a1a1a",
                "disabled_bg": "#f3f3f3", "disabled_fg": "#999999"
            }
        }
        
        self.themed_entries = []
        self.mapping_rows = []
        self.hover_buttons = []

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Main Container
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_label = ttk.Label(header_frame, text="SSH 连接工具 (Native)", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side=tk.LEFT)
        
        self.theme_btn = self.create_hover_button(header_frame, text="☀/🌙", width=5, command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        # --- Basic Connection Info ---
        self.info_frame = ttk.LabelFrame(self.main_frame, text="基本连接信息", padding="10")
        self.info_frame.pack(fill=tk.X, pady=(0, 10))

        # IP Address
        ttk.Label(self.info_frame, text="服务器 IP:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky=tk.W)
        self.ip_entry = self.create_themed_entry(self.info_frame)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

        # Port
        ttk.Label(self.info_frame, text="SSH 端口:", font=("Segoe UI", 9)).grid(row=1, column=0, sticky=tk.W)
        self.port_entry = self.create_themed_entry(self.info_frame)
        self.port_entry.insert(0, "22")
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        # Username
        ttk.Label(self.info_frame, text="用户名:", font=("Segoe UI", 9)).grid(row=2, column=0, sticky=tk.W)
        self.user_entry = self.create_themed_entry(self.info_frame)
        self.user_entry.insert(0, "root")
        self.user_entry.grid(row=2, column=1, padx=5, pady=5)

        # Password
        ttk.Label(self.info_frame, text="密码:", font=("Segoe UI", 9)).grid(row=3, column=0, sticky=tk.W)
        self.pass_entry = self.create_themed_entry(self.info_frame, show="*")
        self.pass_entry.grid(row=3, column=1, padx=5, pady=5)

        # --- Port Forwarding (Collapsible) ---
        self.pf_toggle_btn = self.create_hover_button(self.main_frame, text="▼ 端口映射 (可选)", command=self.toggle_pf_section, relief='flat', anchor='w')
        self.pf_toggle_btn.pack(fill=tk.X, pady=(5, 0))

        self.pf_container = ttk.Frame(self.main_frame)
        self.pf_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.pf_container.pack_forget() # Initially hidden
        
        self.pf_frame = ttk.LabelFrame(self.pf_container, text="", padding="10")
        self.pf_frame.pack(fill=tk.BOTH, expand=True)

        # Controls
        pf_ctrl_frame = ttk.Frame(self.pf_frame)
        pf_ctrl_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.add_map_btn = self.create_hover_button(pf_ctrl_frame, text="+ 添加映射", command=self.add_mapping_row)
        self.add_map_btn.pack(side=tk.LEFT)
        
        ttk.Label(pf_ctrl_frame, text="(支持范围 e.g. 80-85)", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=10)

        # Scrollable Area
        self.canvas = tk.Canvas(self.pf_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.pf_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Connect Button ---
        self.connect_btn = self.create_hover_button(self.main_frame, text="连接 SSH", command=self.connect)
        self.connect_btn.pack(pady=10, fill=tk.X)

        # Footer
        footer_label = ttk.Label(self.main_frame, text="by 高粱NexT", font=("Segoe UI", 8), foreground="gray")
        footer_label.pack(side=tk.BOTTOM)

        self.apply_theme()

    def fade_in(self):
        alpha = self.root.attributes("-alpha")
        if alpha < 1.0:
            alpha += 0.05
            self.root.attributes("-alpha", alpha)
            self.root.after(20, self.fade_in)

    def toggle_pf_section(self):
        if self.pf_container.winfo_viewable():
            self.pf_container.pack_forget()
            self.pf_toggle_btn.config(text="▼ 端口映射 (可选)")
        else:
            self.pf_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10), after=self.pf_toggle_btn)
            self.pf_toggle_btn.config(text="▲ 端口映射 (可选)")
            # Simple fade/slide simulation could go here, but pack/forget is standard for collapsible
            # For smoother slide, we'd need fixed height animation which conflicts with dynamic rows.

    def create_hover_button(self, parent, **kwargs):
        kwargs['font'] = ("Segoe UI", 9)
        kwargs['relief'] = 'flat'
        btn = HoverButton(parent, **kwargs)
        self.hover_buttons.append(btn)
        return btn

    def create_themed_entry(self, parent, width=25, show=None):
        e = tk.Entry(parent, width=width, relief='flat', show=show, font=("Segoe UI", 9))
        self.themed_entries.append(e)
        return e

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def apply_theme(self):
        t = self.themes["dark"] if self.is_dark else self.themes["light"]
        
        self.root.configure(bg=t["bg"])
        self.canvas.configure(bg=t["bg"])
        
        self.style.configure("TFrame", background=t["bg"])
        self.style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 9))
        self.style.configure("TLabelframe", background=t["bg"], foreground=t["fg"])
        self.style.configure("TLabelframe.Label", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 9, "bold"))
        
        # Update Hover Buttons
        for btn in self.hover_buttons:
            try:
                btn.configure(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["btn_hover"], activeforeground=t["btn_fg"])
                btn.default_bg = t["btn_bg"]
                btn.hover_bg = t["btn_hover"]
                btn.default_fg = t["btn_fg"]
            except:
                pass

        # Update Entries
        for entry in self.themed_entries:
            try:
                entry.configure(bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["fg"])
            except:
                pass

    def add_mapping_row(self):
        row = PortMappingRow(self.scrollable_frame, self, len(self.mapping_rows))
        self.mapping_rows.append(row)
        # Re-apply theme to new row's entries
        self.apply_theme()

    def remove_mapping_row(self, row):
        row.destroy()
        if row in self.mapping_rows:
            self.mapping_rows.remove(row)

    def validate_ip(self, ip):
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, ip):
            return False
        parts = ip.split(".")
        return all(0 <= int(part) <= 255 for part in parts)

    def validate_port(self, port_str):
        if not port_str: return False
        if "-" in port_str:
            parts = port_str.split("-")
            if len(parts) != 2: return False
            try:
                start, end = int(parts[0]), int(parts[1])
                return 1 <= start <= 65535 and 1 <= end <= 65535 and start <= end
            except ValueError: return False
        if not port_str.isdigit(): return False
        port = int(port_str)
        return 1 <= port <= 65535

    def parse_port_range(self, port_str):
        if "-" in port_str:
            parts = port_str.split("-")
            return int(parts[0]), int(parts[1]), True
        else:
            p = int(port_str)
            return p, p, False

    def connect(self):
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not self.validate_ip(ip):
            messagebox.showerror("错误", "无效的 IP 地址")
            return
        if not self.validate_port(port):
            messagebox.showerror("错误", "无效的 SSH 端口")
            return
        if not user: user = "root"

        # Collect Port Forwarding Configs
        pf_configs = []
        for row in self.mapping_rows:
            l_port = row.local_port.get().strip()
            r_host = row.remote_host.get().strip()
            r_port = row.remote_port.get().strip()
            
            if not l_port and not r_port: continue # Skip empty rows
            
            if not self.validate_port(l_port) or not self.validate_port(r_port):
                messagebox.showerror("错误", "无效的端口映射配置")
                return
            
            if not r_host: r_host = ip

            l_start, l_end, l_is_range = self.parse_port_range(l_port)
            r_start, r_end, r_is_range = self.parse_port_range(r_port)
            
            l_count = l_end - l_start + 1
            r_count = r_end - r_start + 1
            
            if not l_is_range and r_is_range:
                 messagebox.showerror("错误", "不支持单个本地端口映射到多个远程端口")
                 return
            if l_is_range and r_is_range and l_count != r_count:
                 messagebox.showerror("错误", "端口范围长度不匹配")
                 return

            items = l_count if l_is_range else r_count
            for i in range(items):
                pf_configs.append({
                    'local': l_start + (i if l_is_range else 0),
                    'remote_host': r_host,
                    'remote_port': r_start + (i if r_is_range else 0)
                })

        # Start Connection Thread
        threading.Thread(target=self.start_ssh_session, args=(ip, int(port), user, password, pf_configs), daemon=True).start()

    def start_ssh_session(self, ip, port, user, password, pf_configs):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=user, password=password)
            
            transport = client.get_transport()
            for cfg in pf_configs:
                pf = PortForwarder(cfg['local'], cfg['remote_host'], cfg['remote_port'], transport)
                pf.start()

            channel = client.invoke_shell()
            
            # Pass theme colors to terminal
            t = self.themes["dark"] if self.is_dark else self.themes["light"]
            
            def launch_windows():
                # Open Terminal
                TerminalWindow(self.root, client, channel, 
                             title=f"SSH: {user}@{ip}",
                             bg_color=t["bg"], fg_color=t["fg"])
                # Open Toolbox
                SSHToolbox(self.root, t)

            self.root.after(0, launch_windows)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("连接失败", error_msg))

class SSHToolbox(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.title("SSH 工具箱")
        self.geometry("300x400")
        self.resizable(False, False)
        self.theme = theme
        self.configure(bg=theme["bg"])
        
        # Title
        ttk.Label(self, text="工具箱", font=("Segoe UI", 14, "bold"), 
                 background=theme["bg"], foreground=theme["fg"]).pack(pady=20)
        
        # Buttons
        buttons = [
            ("📁 文件管理", self.show_dev_msg),
            ("🚀 一键安装 X-UI", self.show_dev_msg),
            ("📊 服务器状态", self.show_dev_msg),
            ("🐳 Docker 管理", self.show_dev_msg)
        ]
        
        for text, cmd in buttons:
            btn = HoverButton(self, text=text, command=cmd, font=("Segoe UI", 10),
                            bg=theme["btn_bg"], fg=theme["btn_fg"],
                            hover_bg=theme["btn_hover"], relief='flat', height=2)
            btn.pack(fill=tk.X, padx=30, pady=10)

    def show_dev_msg(self):
        messagebox.showinfo("提示", "本功能在开发中，请耐心等待")

if __name__ == "__main__":
    root = tk.Tk()
    app = SSHGui(root)
    root.mainloop()
