import tkinter as tk
import time
import logging
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque

logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)

class ModernTheme:
    BG = "#1E1E1E"
    SIDEBAR_BG = "#252526"

class MonitoringPanel(tk.Frame):
    def __init__(self, parent, ssh_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.ssh_client = ssh_client
        self.channel = None
        
        self.max_points = 60
        self.cpu_data = deque([0] * self.max_points, maxlen=self.max_points)
        self.mem_data = deque([0] * self.max_points, maxlen=self.max_points)
        self.disk_data = deque([0] * self.max_points, maxlen=self.max_points)
        self.net_rx_data = deque([0] * self.max_points, maxlen=self.max_points)
        self.net_tx_data = deque([0] * self.max_points, maxlen=self.max_points)
        
        self.last_net_rx = 0
        self.last_net_tx = 0
        self.last_net_time = time.time()
        
        # CPU differential stats
        self.last_cpu_total = 0
        self.last_cpu_idle = 0
        
        self.fig = Figure(figsize=(2, 4), dpi=70, facecolor=ModernTheme.SIDEBAR_BG)
        self.fig.subplots_adjust(hspace=0.4, wspace=0.3, left=0.15, right=0.95, top=0.95, bottom=0.05)
        
        self.ax_cpu = self.fig.add_subplot(4, 1, 1)
        self.ax_mem = self.fig.add_subplot(4, 1, 2)
        self.ax_disk = self.fig.add_subplot(4, 1, 3)
        self.ax_net = self.fig.add_subplot(4, 1, 4)
        
        for ax, title in [(self.ax_cpu, 'CPU'), (self.ax_mem, 'MEM'), (self.ax_disk, 'DISK'), (self.ax_net, 'NET')]:
            ax.set_facecolor(ModernTheme.BG)
            ax.set_title(title, color='white', fontsize=8, pad=2)
            ax.set_ylim(0, 100)
            ax.tick_params(colors='#666666', labelsize=6)
            ax.grid(True, alpha=0.2, color='#444444')
            for spine in ax.spines.values():
                spine.set_color('#444444')
        
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        self.monitoring = False
        self.monitoring_session = None
    
    def start_monitoring(self, channel):
        self.channel = channel
        self.monitoring = True
        self.update_data()
    
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitoring_session:
            try:
                self.monitoring_session.close()
            except:
                pass
    
    def get_system_stats(self):
        if not self.channel:
            return None
        
        try:
            transport = self.channel.get_transport()
            if not transport or not transport.is_active():
                return None
            
            if not self.monitoring_session or self.monitoring_session.closed:
                self.monitoring_session = transport.open_session()
            
            session = self.monitoring_session
            # Get raw stats for differential calculation
            cmd = (
                "cat /proc/stat | grep '^cpu ' && "
                "free | grep Mem | awk '{print ($3/$2) * 100.0}' && "
                "df -h / | tail -1 | awk '{gsub(/%/,\"\"); print $5}' && "
                "cat /proc/net/dev"
            )
            
            session.exec_command(cmd)
            session.settimeout(2.0)
            stdout_data = b''
            
            while not session.exit_status_ready():
                if session.recv_ready():
                    stdout_data += session.recv(4096)
                time.sleep(0.05)
            
            while session.recv_ready():
                stdout_data += session.recv(4096)
            
            return self.parse_stats(stdout_data.decode('utf-8', errors='ignore'))
        except Exception as e:
            logging.error(f"Stats error: {e}")
            # Reset session on error
            try:
                if self.monitoring_session:
                    self.monitoring_session.close()
            except: pass
            self.monitoring_session = None
        return None
    
    def parse_stats(self, output):
        try:
            lines = [l.strip() for l in output.split('\n') if l.strip()]
            if len(lines) < 4:
                return None
            
            stats = {}
            
            # 1. CPU (Differential)
            try:
                # Line format: cpu  user nice system idle iowait irq softirq steal guest guest_nice
                cpu_parts = lines[0].split()
                if cpu_parts[0] == 'cpu':
                    # Sum all fields for total
                    values = [int(x) for x in cpu_parts[1:]]
                    total = sum(values)
                    idle = values[3] + values[4] # idle + iowait
                    
                    if self.last_cpu_total > 0:
                        diff_total = total - self.last_cpu_total
                        diff_idle = idle - self.last_cpu_idle
                        if diff_total > 0:
                            usage = 100.0 * (diff_total - diff_idle) / diff_total
                            stats['cpu'] = max(0, min(100, usage))
                        else:
                            stats['cpu'] = 0
                    else:
                        stats['cpu'] = 0 # First run
                        
                    self.last_cpu_total = total
                    self.last_cpu_idle = idle
                else:
                    stats['cpu'] = 0
            except:
                stats['cpu'] = 0
            
            # 2. Memory
            try:
                mem_val = float(lines[1])
                stats['mem'] = max(0, min(100, mem_val))
            except:
                stats['mem'] = 0
            
            # 3. Disk
            try:
                disk_val = float(lines[2].replace('%', '').strip())
                stats['disk'] = max(0, min(100, disk_val))
            except:
                stats['disk'] = 0
            
            # 4. Network (Dynamic Interface Selection)
            try:
                # Find the interface with the most traffic (rx_bytes)
                max_rx = 0
                current_rx = 0
                current_tx = 0
                
                # Parse all network lines (starting from index 3)
                for line in lines[3:]:
                    parts = line.split()
                    if ':' in parts[0]: # Interface name
                        if parts[0].startswith('lo:'): continue # Skip loopback
                        
                        # Format: face |bytes packets errs drop fifo frame compressed multicast|bytes ...
                        # Sometimes there are spaces after colon, sometimes not
                        # If "eth0:" is one token, values start at index 1
                        # If "eth0 :" is two tokens, values start at index 2
                        
                        # Normalize by replacing ':' with ' '
                        clean_line = line.replace(':', ' ')
                        clean_parts = clean_line.split()
                        
                        if len(clean_parts) >= 10:
                            rx = int(clean_parts[1])
                            tx = int(clean_parts[9])
                            
                            if rx > max_rx:
                                max_rx = rx
                                current_rx = rx
                                current_tx = tx
                
                current_time = time.time()
                time_delta = current_time - self.last_net_time
                
                if time_delta > 0.5 and self.last_net_rx > 0:
                    # Calculate rate in KB/s
                    rx_rate = (current_rx - self.last_net_rx) / time_delta / 1024
                    tx_rate = (current_tx - self.last_net_tx) / time_delta / 1024
                    
                    # Scale for display (0-100 scale)
                    # Assume 1000 KB/s (1 MB/s) = 100% for better visualization
                    # This makes the graphs more responsive to network activity
                    stats['net_rx'] = max(0, min(100, rx_rate / 10))  # 1000 KB/s = 100%
                    stats['net_tx'] = max(0, min(100, tx_rate / 10))
                else:
                    stats['net_rx'] = 0
                    stats['net_tx'] = 0
                
                self.last_net_rx = current_rx
                self.last_net_tx = current_tx
                self.last_net_time = current_time
            except:
                stats['net_rx'] = 0
                stats['net_tx'] = 0
            
            return stats
        except Exception as e:
            logging.error(f"Parse error: {e}")
        return None
    
    def update_data(self):
        if not self.monitoring:
            return
        
        stats = self.get_system_stats()
        if stats:
            self.cpu_data.append(stats.get('cpu', 0))
            self.mem_data.append(stats.get('mem', 0))
            self.disk_data.append(stats.get('disk', 0))
            self.net_rx_data.append(stats.get('net_rx', 0))
            self.net_tx_data.append(stats.get('net_tx', 0))
            self.update_plots()
        
        self.after(10000, self.update_data)
    
    def update_plots(self):
        try:
            x = list(range(self.max_points))
            
            # Get current values for display
            cpu_now = self.cpu_data[-1] if self.cpu_data else 0
            mem_now = self.mem_data[-1] if self.mem_data else 0
            disk_now = self.disk_data[-1] if self.disk_data else 0
            rx_now = self.net_rx_data[-1] if self.net_rx_data else 0
            tx_now = self.net_tx_data[-1] if self.net_tx_data else 0
            
            for ax, data, color in [
                (self.ax_cpu, self.cpu_data, '#2472C8'),
                (self.ax_mem, self.mem_data, '#0DBC79'),
                (self.ax_disk, self.disk_data, '#E5E510')
            ]:
                ax.clear()
                ax.plot(x, list(data), color=color, linewidth=1)
                ax.fill_between(x, list(data), alpha=0.3, color=color)
                ax.set_ylim(0, 100)
                ax.tick_params(colors='#666666', labelsize=6)
                ax.grid(True, alpha=0.2, color='#444444')
                ax.set_facecolor(ModernTheme.BG)
            
            self.ax_net.clear()
            self.ax_net.plot(x, list(self.net_rx_data), color='#CD3131', linewidth=1)
            self.ax_net.plot(x, list(self.net_tx_data), color='#BC3FBC', linewidth=1)
            self.ax_net.set_ylim(0, 100)
            self.ax_net.tick_params(colors='#666666', labelsize=6)
            self.ax_net.grid(True, alpha=0.2, color='#444444')
            self.ax_net.set_facecolor(ModernTheme.BG)
            
            # Set titles with current percentage values
            self.ax_cpu.set_title(f'CPU {cpu_now:.1f}%', color='white', fontsize=8, pad=2)
            self.ax_mem.set_title(f'MEM {mem_now:.1f}%', color='white', fontsize=8, pad=2)
            self.ax_disk.set_title(f'DISK {disk_now:.1f}%', color='white', fontsize=8, pad=2)
            self.ax_net.set_title(f'NET ↓{rx_now:.1f}% ↑{tx_now:.1f}%', color='white', fontsize=8, pad=2)
            
            self.canvas.draw()
        except Exception as e:
            logging.error(f"Plot error: {e}")
