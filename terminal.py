import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, ttk
import paramiko
import threading
import sys
import time
import argparse
import logging
import re
from monitoring_panel import MonitoringPanel

# Setup logging
logging.basicConfig(filename='terminal_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ModernTheme:
    BG = "#1E1E1E"       # Main background
    SIDEBAR_BG = "#252526"
    FG = "#CCCCCC"
    ACCENT = "#007ACC"
    SELECTION = "#264F78"
    
    ANSI_COLORS = {
        0: "#333333", 1: "#CD3131", 2: "#0DBC79", 3: "#E5E510",
        4: "#2472C8", 5: "#BC3FBC", 6: "#11A8CD", 7: "#E5E5E5",
        8: "#666666", 9: "#F14C4C", 10: "#23D18B", 11: "#F5F543",
        12: "#3B8EEA", 13: "#D670D6", 14: "#29B8DB", 15: "#FFFFFF"
    }

class AnsiColorText(tk.Text):
    """Text widget with ANSI color support and blinking cursor"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ansi_regex = re.compile(r'(\x1b\[[\?]?[0-9;]*[a-zA-Z]|\x08|\r|\n|\x07)')
        self.current_tags = set()
        
        self.tag_configure("bold", font=("Consolas", 11, "bold"))
        for code, color in ModernTheme.ANSI_COLORS.items():
            self.tag_configure(f"fg_{30+code}", foreground=color)
            self.tag_configure(f"fg_{90+code}", foreground=color)
            self.tag_configure(f"bg_{40+code}", background=color)
            self.tag_configure(f"bg_{100+code}", background=color)
        
        # Initialize terminal cursor at the end
        self.mark_set("term_cursor", "end-1c")
        self.mark_gravity("term_cursor", tk.RIGHT)
        
        # Cursor Visuals - Green block cursor using a Frame
        self.cursor_frame = tk.Frame(self, bg="#0DBC79", width=1, height=1)
        self.cursor_on = True
        self.blink_job = None

    def start_blink(self):
        self.blink_cursor()

    def stop_blink(self):
        if self.blink_job:
            self.after_cancel(self.blink_job)
            self.blink_job = None
        self.cursor_frame.place_forget()

    def blink_cursor(self):
        if self.cursor_on:
            # Show cursor
            # Temporarily enable widget to get bbox
            current_state = str(self['state'])
            if current_state == 'disabled':
                self.configure(state='normal')
            
            try:
                # Get coordinates of the cursor
                bbox = self.bbox("term_cursor")
                if bbox:
                    x, y, w, h = bbox
                    # IMPORTANT: Always use fixed character width, not bbox width
                    # bbox width can be huge at end of line, causing the entire line to be highlighted
                    char_width = 9  # Fixed width for one character (Consolas 11pt)
                    self.cursor_frame.place(x=x, y=y, width=char_width, height=h)
                    self.cursor_frame.lift() # Ensure it's on top
                else:
                    self.cursor_frame.place_forget()
            except:
                self.cursor_frame.place_forget()
            
            # Restore state
            if current_state == 'disabled':
                self.configure(state='disabled')
        else:
            # Hide cursor
            self.cursor_frame.place_forget()
        self.cursor_on = not self.cursor_on  # Toggle on/off for blinking
        self.blink_job = self.after(500, self.blink_cursor)
    
    def force_cursor_update(self):
        """Force cursor to show and update position immediately"""
        if self.blink_job:
            self.after_cancel(self.blink_job)
        
        # Always show cursor when forcing update
        self.cursor_on = True
        
        # Temporarily enable widget to get bbox (disabled widgets may not return bbox correctly)
        current_state = str(self['state'])
        if current_state == 'disabled':
            self.configure(state='normal')
        
        try:
            bbox = self.bbox("term_cursor")
            if bbox:
                x, y, w, h = bbox
                char_width = 9
                self.cursor_frame.place(x=x, y=y, width=char_width, height=h)
                self.cursor_frame.lift()
            else:
                self.cursor_frame.place_forget()
        except:
            self.cursor_frame.place_forget()
        
        # Restore state
        if current_state == 'disabled':
            self.configure(state='disabled')
        
        # Restart blinking cycle from 'on' state
        self.blink_job = self.after(500, self.blink_cursor)
    
    def write(self, text):
        self.configure(state='normal')
        
        parts = self.ansi_regex.split(text)
        for part in parts:
            if not part: continue
            
            if part == '\x08':
                if not self.compare("term_cursor", "==", "1.0"):
                    self.mark_set("term_cursor", "term_cursor-1c")
                continue
            
            if part == '\r':
                self.mark_set("term_cursor", "term_cursor linestart")
                continue
            
            if part == '\n':
                current_line = int(self.index("term_cursor").split('.')[0])
                last_line = int(self.index("end-1c").split('.')[0])
                if current_line >= last_line:
                    self.mark_set("term_cursor", "end-1c")
                    self.insert("term_cursor", "\n")
                else:
                    self.mark_set("term_cursor", "term_cursor + 1 lines")
                continue
            
            if part == '\x07': continue
            
            if part.startswith('\x1b['):
                code_body = part[2:]
                if code_body.endswith('K'):
                    if code_body == 'K' or code_body == '0K':
                        self.delete("term_cursor", "term_cursor lineend")
                    elif code_body == '1K':
                        self.delete("term_cursor linestart", "term_cursor")
                    elif code_body == '2K':
                        self.delete("term_cursor linestart", "term_cursor lineend")
                    continue
                
                if code_body.endswith('J'):
                    if code_body == '2J':
                        self.delete("1.0", "end")
                        self.mark_set("term_cursor", "1.0")
                    continue

                if code_body.endswith('P'): # Delete Character (DCH)
                    try:
                        count = int(code_body[:-1]) if code_body[:-1] else 1
                        self.delete("term_cursor", f"term_cursor +{count} chars")
                    except: pass
                    continue
                    
                if code_body.endswith('X'): # Erase Character (ECH)
                    try:
                        count = int(code_body[:-1]) if code_body[:-1] else 1
                        # Replace with spaces
                        self.insert("term_cursor", " " * count)
                        self.delete("term_cursor", f"term_cursor +{count} chars")
                        # Move cursor back? No, ECH usually doesn't move cursor, but insert moves it.
                        # Actually ECH just overwrites with space and doesn't move cursor.
                        # So we insert spaces then move cursor back.
                        self.mark_set("term_cursor", f"term_cursor -{count} chars")
                    except: pass
                    continue

                if code_body.endswith('@'): # Insert Character (ICH)
                    try:
                        count = int(code_body[:-1]) if code_body[:-1] else 1
                        self.insert("term_cursor", " " * count)
                        self.mark_set("term_cursor", f"term_cursor -{count} chars")
                    except: pass
                    continue

                if code_body.endswith('H') or code_body.endswith('f'): # Cursor Position
                    try:
                        parts = code_body[:-1].split(';')
                        row = int(parts[0]) if parts[0] else 1
                        col = int(parts[1]) if len(parts) > 1 and parts[1] else 1
                        # Tkinter text is 1-based line, 0-based char. ANSI is 1-based both.
                        self.mark_set("term_cursor", f"{row}.{col-1}")
                    except: pass
                    continue
                
                if code_body.startswith('?'): continue
                
                if code_body.endswith('A'):
                    try:
                        rows = int(code_body[:-1]) if code_body[:-1] else 1
                        self.mark_set("term_cursor", f"term_cursor -{rows} lines")
                    except: pass
                elif code_body.endswith('B'):
                    try:
                        rows = int(code_body[:-1]) if code_body[:-1] else 1
                        self.mark_set("term_cursor", f"term_cursor +{rows} lines")
                    except: pass
                elif code_body.endswith('C'):
                    try:
                        cols = int(code_body[:-1]) if code_body[:-1] else 1
                        self.mark_set("term_cursor", f"term_cursor +{cols} chars")
                    except: pass
                elif code_body.endswith('D'):
                    try:
                        cols = int(code_body[:-1]) if code_body[:-1] else 1
                        self.mark_set("term_cursor", f"term_cursor -{cols} chars")
                    except: pass
                
                if code_body.endswith('m'):
                    params_str = code_body[:-1]
                    params = [int(p) for p in params_str.split(';') if p.isdigit()]
                    if not params: params = [0]
                    for p in params:
                        if p == 0:
                            self.current_tags.clear()
                        elif p == 1:
                            self.current_tags.add("bold")
                        elif 30 <= p <= 37:
                            self.current_tags = {t for t in self.current_tags if not t.startswith("fg_")}
                            self.current_tags.add(f"fg_{p}")
                        elif 40 <= p <= 47:
                            self.current_tags = {t for t in self.current_tags if not t.startswith("bg_")}
                            self.current_tags.add(f"bg_{p}")
                        elif 90 <= p <= 97:
                            self.current_tags = {t for t in self.current_tags if not t.startswith("fg_")}
                            self.current_tags.add(f"fg_{p}")
                        elif 100 <= p <= 107:
                            self.current_tags = {t for t in self.current_tags if not t.startswith("bg_")}
                            self.current_tags.add(f"bg_{p}")
                continue
            
            for char in part:
                # Robust VT100 logic:
                # Check if we are at the end of the line using 'lineend' modifier
                # This is more reliable than get() which might return newline char
                
                is_at_line_end = self.compare("term_cursor", "==", "term_cursor lineend")
                
                if is_at_line_end:
                    # At end of line - insert (append)
                    self.insert("term_cursor", char, tuple(self.current_tags))
                else:
                    # In middle of line - check if next char is newline (just in case)
                    next_char = self.get("term_cursor")
                    if next_char == "\n":
                        self.insert("term_cursor", char, tuple(self.current_tags))
                    else:
                        # Overwrite
                        self.delete("term_cursor")
                        self.insert("term_cursor", char, tuple(self.current_tags))
        
        self.see("term_cursor")
        self.mark_set("insert", "term_cursor")
        self.configure(state='disabled')
        self.force_cursor_update()

class TerminalWindow(tk.Tk):
    def __init__(self, ip, port, user, password, theme_mode="dark", command=None):
        super().__init__()
        self.title("SSH Terminal")
        self.geometry("1000x700")
        self.configure(bg=ModernTheme.BG)
        
        self.ip = ip
        self.port = int(port)
        self.user = user
        self.password = password
        self.command = command
        
        # Sidebar
        self.sidebar = tk.Frame(self, bg=ModernTheme.SIDEBAR_BG, width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        tk.Label(self.sidebar, text="主机列表", bg=ModernTheme.SIDEBAR_BG, fg="#555555", 
                font=("Microsoft YaHei UI", 9, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(20, 5))
        
        self.host_item = tk.Frame(self.sidebar, bg=ModernTheme.SELECTION, height=40)
        self.host_item.pack(fill=tk.X, padx=5)
        self.host_item.pack_propagate(False)
        
        tk.Label(self.host_item, text="⬤", fg="#0DBC79", bg=ModernTheme.SELECTION, 
                font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(10, 5))
        tk.Label(self.host_item, text=f"{user}@{ip}", fg="white", bg=ModernTheme.SELECTION, 
                font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        
        tk.Label(self.sidebar, text="服务器监控", bg=ModernTheme.SIDEBAR_BG, fg="#555555", 
                font=("Microsoft YaHei UI", 9, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(20, 5))
        self.monitoring_panel = MonitoringPanel(self.sidebar, bg=ModernTheme.SIDEBAR_BG)
        self.monitoring_panel.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Main Area
        self.main_area = tk.Frame(self, bg=ModernTheme.BG)
        self.main_area.pack(side=tk.LEFT, expand=True, fill='both')
        
        self.header = tk.Frame(self.main_area, bg=ModernTheme.BG, height=35)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)
        
        tk.Label(self.header, text=f" {user}@{ip} ", bg=ModernTheme.BG, fg="white", 
                font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, padx=10, pady=5)
        
        self.term_frame = tk.Frame(self.main_area, bg=ModernTheme.BG)
        self.term_frame.pack(expand=True, fill='both', padx=10, pady=(0, 10))
        
        # Scrollbar removed as per user request
        
        self.text_area = AnsiColorText(self.term_frame, state='normal',  # Start in normal state 
                                       bg=ModernTheme.BG, fg=ModernTheme.FG, 
                                       font=("Consolas", 11), 
                                       insertbackground="white",
                                       selectbackground=ModernTheme.SELECTION,
                                       bd=0, highlightthickness=0)
        self.text_area.pack(side=tk.LEFT, expand=True, fill='both')
        self.text_area.focus_force()
        
        # Start cursor blinking immediately
        self.text_area.start_blink()
        
        self.client = None
        self.channel = None
        self.running = True
        self.input_buffer = ""
        
        self.text_area.bind("<KeyPress>", self.on_key)
        self.text_area.bind("<Return>", self.on_enter)
        self.text_area.bind("<BackSpace>", self.on_backspace)
        self.text_area.bind("<Up>", lambda e: self.send_control_sequence("\x1b[A"))
        self.text_area.bind("<Down>", lambda e: self.send_control_sequence("\x1b[B"))
        self.text_area.bind("<Right>", lambda e: self.send_control_sequence("\x1b[C"))
        self.text_area.bind("<Left>", lambda e: self.send_control_sequence("\x1b[D"))
        self.text_area.bind("<Home>", lambda e: self.send_control_sequence("\x1b[H"))
        self.text_area.bind("<End>", lambda e: self.send_control_sequence("\x1b[F"))
        self.text_area.bind("<Control-c>", self.send_interrupt)
        self.text_area.bind("<Control-v>", self.paste_from_clipboard)
        self.text_area.bind("<Button-3>", self.show_context_menu)
        self.text_area.bind("<Button-1>", self.on_mouse_click)
        
        self.connect_thread = threading.Thread(target=self.connect_ssh, daemon=True)
        self.connect_thread.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def connect_ssh(self):
        try:
            self.update_terminal(f"正在连接到 {self.user}@{self.ip}...\n")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.ip, port=self.port, username=self.user, password=self.password)
            self.client.get_transport().set_keepalive(30)
            
            self.channel = self.client.invoke_shell(term='xterm-256color', width=120, height=40)
            self.update_terminal("已连接。\n")
            
            self.channel.send("\n")
            self.channel.send("export LANG=zh_CN.UTF-8\n")
            
            if self.command:
                self.update_terminal(f"正在执行: {self.command}\n")
                self.channel.send(self.command + "\n")
            
            self.recv_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.recv_thread.start()
            
            self.after(1000, lambda: self.monitoring_panel.start_monitoring(self.channel))
        except Exception as e:
            self.update_terminal(f"连接失败: {str(e)}\n")
    
    def update_terminal(self, data):
        self.text_area.write(data)
    
    def receive_data(self):
        try:
            while getattr(self, 'running', False) and self.channel:
                if self.channel.recv_ready():
                    try:
                        data = self.channel.recv(4096).decode('utf-8', errors='ignore')
                        if not data: break
                        self.after(0, self.update_terminal, data)
                    except: break
                time.sleep(0.01)
        except: pass
    
    def on_key(self, event):
        if not self.channel: return "break"
        if len(event.char) > 0 and ord(event.char) >= 32:
            try:
                self.input_buffer += event.char
                self.channel.send(event.char)
            except OSError:
                self.update_terminal("\n[连接已断开]\n")
                self.channel = None
            return "break"
    
    def on_enter(self, event):
        if not self.channel: return "break"
        if "rm -rf /*" in self.input_buffer.strip():
            if messagebox.askyesno("危险命令警告", "警告：您即将执行 'rm -rf /*'。\n此操作将删除系统上的所有内容。\n\n您确定要继续吗?", 
                                   icon='warning', default='no'):
                pwd_check = simpledialog.askstring("密码验证", "请输入您的SSH密码：", show='*', parent=self)
                if pwd_check != self.password:
                    messagebox.showerror("错误", "密码错误。")
                    self.input_buffer = ""
                    try: self.channel.send("\x03")
                    except: pass
                    return "break"
            else:
                self.input_buffer = ""
                try: self.channel.send("\x03")
                except: pass
                return "break"
        try:
            self.channel.send("\n")
            self.input_buffer = ""
        except OSError:
            self.update_terminal("\n[连接已断开]\n")
            self.channel = None
        return "break"
    
    def on_backspace(self, event):
        if not self.channel: return "break"
        try:
            if len(self.input_buffer) > 0:
                self.input_buffer = self.input_buffer[:-1]
            self.channel.send("\x7f")
        except OSError:
            self.update_terminal("\n[连接已断开]\n")
            self.channel = None
        return "break"
    
    def send_control_sequence(self, seq):
        if not self.channel: return "break"
        try:
            self.channel.send(seq)
        except OSError:
            self.update_terminal("\n[连接已断开]\n")
            self.channel = None
        return "break"
    
    def send_interrupt(self, event=None):
        if not self.channel: return "break"
        try:
            self.channel.send("\x03")
            self.input_buffer = ""
        except OSError:
            self.update_terminal("\n[连接已断开]\n")
            self.channel = None
        return "break"

    def paste_from_clipboard(self, event=None):
        if not self.channel: return "break"
        try:
            data = self.clipboard_get()
            if data:
                self.input_buffer += data
                self.channel.send(data)
        except OSError:
            self.update_terminal("\n[连接已断开]\n")
            self.channel = None
        except: pass
        return "break"
    
    def show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="复制", command=self.copy_selection)
        menu.add_command(label="粘贴", command=self.paste_from_clipboard)
        menu.tk_popup(event.x_root, event.y_root)
    
    def copy_selection(self):
        try:
            selected_text = self.text_area.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except: pass
        
    def on_mouse_click(self, event):
        """Handle mouse click to move cursor via arrow keys"""
        if not self.channel: return "break"
        try:
            # Get click position index
            click_index = self.text_area.index(f"@{event.x},{event.y}")
            cursor_index = self.text_area.index("term_cursor")
            
            # Calculate line and column difference
            click_line, click_col = map(int, click_index.split('.'))
            cursor_line, cursor_col = map(int, cursor_index.split('.'))
            
            # Only allow moving on the same line (simple implementation)
            if click_line == cursor_line:
                diff = click_col - cursor_col
                if diff > 0:
                    # Move right
                    self.channel.send("\x1b[C" * diff)
                elif diff < 0:
                    # Move left
                    self.channel.send("\x1b[D" * abs(diff))
            
            self.text_area.focus_force()
        except: pass
        return "break"
    
    def on_close(self):
        self.running = False
        self.text_area.stop_blink()
        self.monitoring_panel.stop_monitoring()
        if self.client:
            try: self.client.close()
            except: pass
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
