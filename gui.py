import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import paramiko
import threading
import socket
import sys
import re
import select
import time
import os
import stat
import subprocess
import sys
from datetime import datetime
from tkinter import filedialog



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
        
        self.title_label = ttk.Label(header_frame, text="SSH simple", font=("Segoe UI", 16, "bold"))
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

            # Pass theme colors to terminal
            t = self.themes["dark"] if self.is_dark else self.themes["light"]

            def launch_windows():
                # Open Toolbox only
                SSHToolbox(self.root, t, client, user, ip, port, password)

            self.root.after(0, launch_windows)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("连接失败", error_msg))

            self.root.after(0, lambda: messagebox.showerror("连接失败", error_msg))

class TextEditorWindow(tk.Toplevel):
    def __init__(self, master, sftp, remote_path, theme):
        super().__init__(master)
        self.title(f"编辑: {remote_path}")
        self.geometry("800x600")
        self.sftp = sftp
        self.remote_path = remote_path
        self.theme = theme
        self.configure(bg=theme["bg"])

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        HoverButton(toolbar, text="💾 保存", command=self.save_file,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)
        HoverButton(toolbar, text="🔄 重载", command=self.load_file,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)

        # Text Area
        self.text_area = scrolledtext.ScrolledText(self, undo=True, font=("Consolas", 11))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.load_file()

    def load_file(self):
        try:
            with self.sftp.open(self.remote_path, 'r') as f:
                content = f.read().decode('utf-8')
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', content)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件: {str(e)}")

    def save_file(self):
        try:
            content = self.text_area.get('1.0', tk.END)
            with self.sftp.open(self.remote_path, 'w') as f:
                f.write(content.encode('utf-8'))
            messagebox.showinfo("成功", "文件已保存")
        except Exception as e:
            messagebox.showerror("错误", f"无法保存文件: {str(e)}")

class FileManagerWindow(tk.Toplevel):
    def __init__(self, master, client, theme):
        super().__init__(master)
        self.title("文件管理")
        self.geometry("900x600")
        self.client = client
        self.theme = theme
        self.configure(bg=theme["bg"])
        
        self.sftp = self.client.open_sftp()
        self.current_path = "/"
        self.clipboard = None # {path, op='cut'|'copy'}

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        HoverButton(toolbar, text="⬆ 上一级", command=self.go_up, width=8,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)
        HoverButton(toolbar, text="🏠 根目录", command=lambda: self.navigate("/"), width=8,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)
        HoverButton(toolbar, text="🔄 刷新", command=self.refresh, width=6,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        HoverButton(toolbar, text="📤 上传", command=self.upload_file, width=6,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)
        HoverButton(toolbar, text="📁 新建文件夹", command=self.new_folder, width=10,
                   bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"]).pack(side=tk.LEFT, padx=2)

        # Address Bar
        self.addr_var = tk.StringVar()
        addr_entry = tk.Entry(toolbar, textvariable=self.addr_var, font=("Segoe UI", 9))
        addr_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        addr_entry.bind("<Return>", lambda e: self.navigate(self.addr_var.get()))

        # File List
        columns = ("name", "size", "type", "mtime")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="名称")
        self.tree.heading("size", text="大小")
        self.tree.heading("type", text="类型")
        self.tree.heading("mtime", text="修改时间")
        
        self.tree.column("name", width=300)
        self.tree.column("size", width=100)
        self.tree.column("type", width=80)
        self.tree.column("mtime", width=150)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        sb = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        # Bindings
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Context Menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="打开/进入", command=self.on_double_click)
        self.menu.add_command(label="编辑 (文本)", command=self.edit_file)
        self.menu.add_separator()
        self.menu.add_command(label="下载", command=self.download_file)
        self.menu.add_separator()
        self.menu.add_command(label="复制", command=lambda: self.set_clipboard('copy'))
        self.menu.add_command(label="剪切", command=lambda: self.set_clipboard('cut'))
        self.menu.add_command(label="粘贴", command=self.paste_file)
        self.menu.add_separator()
        self.menu.add_command(label="重命名", command=self.rename_item)
        self.menu.add_command(label="删除", command=self.delete_item)

        self.navigate("/")

    def navigate(self, path):
        try:
            self.sftp.chdir(path)
            self.current_path = self.sftp.getcwd()
            self.addr_var.set(self.current_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("错误", f"无法进入目录: {str(e)}")

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            files = self.sftp.listdir_attr(self.current_path)
            # Sort: folders first, then files
            files.sort(key=lambda x: (not stat.S_ISDIR(x.st_mode), x.filename))
            
            for f in files:
                is_dir = stat.S_ISDIR(f.st_mode)
                ftype = "文件夹" if is_dir else "文件"
                size = f"{f.st_size / 1024:.1f} KB" if not is_dir else ""
                mtime = datetime.fromtimestamp(f.st_mtime).strftime('%Y-%m-%d %H:%M')
                
                icon = "📁 " if is_dir else "📄 "
                self.tree.insert("", "end", iid=f.filename, values=(icon + f.filename, size, ftype, mtime))
        except Exception as e:
            messagebox.showerror("错误", f"刷新失败: {str(e)}")

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent == self.current_path: return # Root
        self.navigate(parent)

    def on_double_click(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        name = sel[0]
        # Remove icon
        # Actually iid is just filename based on insert above
        
        try:
            attr = self.sftp.stat(self.current_path + "/" + name)
            if stat.S_ISDIR(attr.st_mode):
                self.navigate(self.current_path + "/" + name)
            else:
                self.edit_file()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def upload_file(self):
        local_path = filedialog.askopenfilename()
        if local_path:
            filename = os.path.basename(local_path)
            remote_path = self.current_path + "/" + filename
            try:
                self.sftp.put(local_path, remote_path)
                messagebox.showinfo("成功", "上传完成")
                self.refresh()
            except Exception as e:
                messagebox.showerror("错误", f"上传失败: {str(e)}")

    def download_file(self):
        sel = self.tree.selection()
        if not sel: return
        filename = sel[0]
        remote_path = self.current_path + "/" + filename
        
        local_path = filedialog.asksaveasfilename(initialfile=filename)
        if local_path:
            try:
                self.sftp.get(remote_path, local_path)
                messagebox.showinfo("成功", "下载完成")
            except Exception as e:
                messagebox.showerror("错误", f"下载失败: {str(e)}")

    def edit_file(self):
        sel = self.tree.selection()
        if not sel: return
        filename = sel[0]
        remote_path = self.current_path + "/" + filename
        
        # Simple check if binary
        # For now assume text
        TextEditorWindow(self, self.sftp, remote_path, self.theme)

    def new_folder(self):
        # Simple input dialog needed, using simpledialog or custom
        # For brevity, using a simple Toplevel or just a fixed name?
        # Let's use a quick custom dialog since we don't have simpledialog imported
        # Or just import simpledialog
        pass # To be implemented or use generic name

    def delete_item(self):
        sel = self.tree.selection()
        if not sel: return
        filename = sel[0]
        path = self.current_path + "/" + filename
        if messagebox.askyesno("确认", f"确定删除 {filename} 吗?"):
            try:
                try:
                    self.sftp.remove(path)
                except:
                    self.sftp.rmdir(path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")

    def rename_item(self):
        # Needs input dialog
        pass

    def set_clipboard(self, op):
        sel = self.tree.selection()
        if not sel: return
        self.clipboard = {'path': self.current_path + "/" + sel[0], 'op': op, 'name': sel[0]}

    def paste_file(self):
        if not self.clipboard: return
        src = self.clipboard['path']
        dst = self.current_path + "/" + self.clipboard['name']
        
        try:
            if self.clipboard['op'] == 'copy':
                # SFTP doesn't have remote copy. We must read and write.
                # This is slow for large files.
                with self.sftp.open(src, 'rb') as f_src:
                    with self.sftp.open(dst, 'wb') as f_dst:
                        f_dst.write(f_src.read())
            elif self.clipboard['op'] == 'cut':
                self.sftp.rename(src, dst)
            
            self.refresh()
            self.clipboard = None
        except Exception as e:
            messagebox.showerror("错误", f"粘贴失败: {str(e)}")

class SSHToolbox(tk.Toplevel):
    def __init__(self, master, theme, client, user, ip, port, password):
        super().__init__(master)
        self.title("SSH 工具箱")
        self.geometry("350x450")
        self.resizable(False, False)
        self.theme = theme
        self.client = client
        self.user = user
        self.ip = ip
        self.port = str(port)
        self.password = password
        self.configure(bg=theme["bg"])
        
        # Status Section
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.status_lbl = ttk.Label(status_frame, text=f"🟢 已连接: {ip}", 
                             font=("Segoe UI", 10, "bold"), foreground="green", background=theme["bg"])
        self.status_lbl.pack(side=tk.LEFT)
        
        cmd_btn = HoverButton(status_frame, text="💻 终端", command=self.open_terminal,
                            font=("Segoe UI", 9), width=8,
                            bg=theme["btn_bg"], fg=theme["btn_fg"],
                            hover_bg=theme["btn_hover"], relief='flat')
        cmd_btn.pack(side=tk.RIGHT)
        
        # Buttons
        buttons = [
            ("📁 文件管理", self.open_file_manager),
            ("🚀 3x-ui 一键安装", self.install_3x_ui),
            ("📊 服务器状态", self.show_dev_msg),
            ("🐳 Docker 管理", self.show_dev_msg)
        ]
        
        for text, cmd in buttons:
            btn = HoverButton(self, text=text, command=cmd, font=("Segoe UI", 10),
                            bg=theme["btn_bg"], fg=theme["btn_fg"],
                            hover_bg=theme["btn_hover"], relief='flat', height=2)
            btn.pack(fill=tk.X, padx=30, pady=10)
            
        # Latency Monitor (Bottom Right)
        self.latency_frame = tk.Frame(self, bg=theme["bg"])
        self.latency_frame.pack(side=tk.BOTTOM, anchor=tk.E, padx=10, pady=10)
        
        self.latency_label = tk.Label(self.latency_frame, text="延迟: -- ms", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9))
        self.latency_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.test_latency_btn = HoverButton(self.latency_frame, text="测试延迟", command=self.start_latency_test,
                                          bg=theme["btn_bg"], fg=theme["btn_fg"], hover_bg=theme["btn_hover"],
                                          font=("Segoe UI", 8), width=8, relief='flat')
        self.test_latency_btn.pack(side=tk.LEFT)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.monitor_connection()
        
        # Auto-ping on start
        self.after(500, self.start_latency_test)

    def start_latency_test(self):
        self.latency_label.config(text="正在测试...")
        self.test_latency_btn.config(state="disabled")
        threading.Thread(target=self.run_ssh_latency_test, daemon=True).start()

    def run_ssh_latency_test(self):
        try:
            if not self.client or not self.client.get_transport() or not self.client.get_transport().is_active():
                 self.after(0, lambda: self.latency_label.config(text="延迟: 未连接"))
                 return

            start_time = time.time()
            # Execute a lightweight command
            stdin, stdout, stderr = self.client.exec_command('echo 1', timeout=5)
            stdout.read() # Wait for completion
            end_time = time.time()
            
            latency = int((end_time - start_time) * 1000)
            self.after(0, lambda: self.latency_label.config(text=f"延迟: {latency} ms"))
            
        except Exception as e:
            self.after(0, lambda: self.latency_label.config(text="延迟: 错误"))
        finally:
            self.after(0, lambda: self.test_latency_btn.config(state="normal"))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.monitor_connection()

    def monitor_connection(self):
        if self.client and self.client.get_transport() and self.client.get_transport().is_active():
             self.status_lbl.config(text=f"🟢 已连接: {self.ip}", foreground="green")
             self.after(2000, self.monitor_connection)
        else:
             self.status_lbl.config(text=f"🔴 已断开: {self.ip}", foreground="red")

    def open_terminal(self):
        if self.client and self.client.get_transport() and self.client.get_transport().is_active():
            try:
                channel = self.client.invoke_shell()
                TerminalWindow(self.master, self.client, channel, 
                             title=f"SSH: {self.user}@{self.ip}",
                             bg_color=self.theme["bg"], fg_color=self.theme["fg"])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开终端: {str(e)}")
        else:
            messagebox.showerror("错误", "连接已断开")

    def on_close(self):
        try:
            self.client.close()
        except:
            pass
        self.destroy()

    def open_terminal(self):
        # Use terminal.py for the independent SSH command box (Tkinter based)
        theme_mode = "dark" if self.theme["bg"] == "#202020" else "light"
        args = [sys.executable, "terminal.py", "-u", self.user, "-h", self.ip, "-p", self.port, "-pwd", self.password, "-t", theme_mode]
        try:
            subprocess.Popen(args)
        except Exception as e:
            messagebox.showerror("错误", f"无法启动 terminal.py: {str(e)}")

    def open_file_manager(self):
        if self.client:
            try:
                FileManagerWindow(self.master, self.client, self.theme)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件管理: {str(e)}")
        else:
             messagebox.showerror("错误", "未连接")

    def install_3x_ui(self):
        if messagebox.askyesno("安装确认", "是否安装 3x-ui?"):
            try:
                cmd = "bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)"
                theme_mode = "dark" if self.theme["bg"] == "#202020" else "light"
                args = [sys.executable, "terminal.py", "-u", self.user, "-h", self.ip, "-p", self.port, "-pwd", self.password, "-t", theme_mode, "-cmd", cmd]
                subprocess.Popen(args)
            except Exception as e:
                messagebox.showerror("错误", f"无法启动安装进程: {str(e)}")

    def show_dev_msg(self):
        messagebox.showinfo("提示", "本功能在开发中，请耐心等待")


if __name__ == "__main__":
    root = tk.Tk()
    app = SSHGui(root)
    root.mainloop()
