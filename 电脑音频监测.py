import tkinter as tk
from tkinter import ttk
import threading
import time
from spi_comm import SPIAdapter
from vfd_driver import VFDScreen
from audio_monitor import AudioProcessor


class VFDControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VFD 频谱控制器")
        self.root.geometry("400x380")

        # 运行控制
        self.is_running = False
        self.stop_signal = threading.Event()
        self.worker_thread = None

        # 初始化模块
        self.spi = SPIAdapter()
        self.spi.open()
        self.vfd = VFDScreen(self.spi)
        self.vfd.init_device()
        self.audio = AudioProcessor()

        self.create_widgets()

    def create_widgets(self):
        # --- 声音源选择部分保持不变 ---
        dev_frame = ttk.LabelFrame(self.root, text="声音源选择 (监听停止时可修改)")
        dev_frame.pack(padx=10, pady=10, fill="x")

        devices = self.audio.get_device_list()
        self.dev_map = {f"{'[内录]' if d['is_loopback'] else '[麦克]'}: {d['name']}": d['index'] for d in devices}

        self.combo = ttk.Combobox(dev_frame, values=list(self.dev_map.keys()), state="readonly")
        if self.dev_map: self.combo.current(0)
        self.combo.pack(padx=10, pady=10, fill="x")

        # --- 参数调节部分：加入了 Label 文字标明 ---
        param_frame = ttk.LabelFrame(self.root, text="实时参数设置")
        param_frame.pack(padx=10, pady=5, fill="x")

        # 增益部分
        ttk.Label(param_frame, text="显示增益 (Gain):").pack(anchor="w", padx=10, pady=(5, 0))
        self.gain_scale = ttk.Scale(param_frame, from_=1.0, to=10.0, value=6.0, command=lambda e: self.sync_params())
        self.gain_scale.pack(fill="x", padx=10, pady=(0, 5))

        # 基值部分
        ttk.Label(param_frame, text="噪声基值 (Threshold):").pack(anchor="w", padx=10, pady=(5, 0))
        self.th_scale = ttk.Scale(param_frame, from_=2.0, to=6.0, value=4.0, command=lambda e: self.sync_params())
        self.th_scale.pack(fill="x", padx=10, pady=(0, 10))

        # --- 控制按钮部分保持不变 ---
        self.btn = ttk.Button(self.root, text="启动监听", command=self.toggle)
        self.btn.pack(pady=20)

    def sync_params(self):
        self.audio.global_gain = self.gain_scale.get()
        self.audio.base_threshold = self.th_scale.get()

    def spectrum_worker(self, device_idx):
        """后台线程：只管读和写，不再涉及复杂的切换逻辑"""
        if self.audio.open_stream(device_idx):
            self.sync_params()
            while not self.stop_signal.is_set():
                levels = self.audio.get_audio_frame()
                self.vfd.display_spectrum(levels)
                time.sleep(0.005)

            # 停止后清理
            self.audio.close_stream()
            self.vfd.clear()

    def toggle(self):
        if not self.is_running:
            # --- 启动逻辑 ---
            selected_name = self.combo.get()
            if not selected_name: return

            idx = self.dev_map[selected_name]

            # 1. 锁定 UI
            self.combo.config(state="disabled")
            self.btn.config(text="停止监听")

            # 2. 启动线程
            self.stop_signal.clear()
            self.worker_thread = threading.Thread(target=self.spectrum_worker, args=(idx,), daemon=True)
            self.worker_thread.start()
            self.is_running = True
        else:
            # --- 停止逻辑 ---
            self.btn.config(text="正在停止...")
            self.btn.config(state="disabled")

            # 1. 发送停止信号并等待线程结束
            self.stop_signal.set()
            if self.worker_thread:
                self.worker_thread.join(timeout=1.0)

            # 2. 解锁 UI
            self.combo.config(state="readonly")
            self.btn.config(text="启动监听")
            self.btn.config(state="normal")
            self.is_running = False

    def on_close(self):
        self.stop_signal.set()
        if self.worker_thread: self.worker_thread.join(timeout=0.5)
        self.spi.close()
        self.audio.terminate()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VFDControllerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()