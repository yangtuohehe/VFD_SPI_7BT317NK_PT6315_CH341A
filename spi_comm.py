import ctypes
import os
import threading
from ctypes import c_ubyte


class SPIAdapter:
    def __init__(self, dll_name=r'C:\Users\xz\Desktop\资料\CH341PAR\CH341PAR\CH341DLLA64.DLL'):
        try:
            # 尝试加载指定路径
            self.lib = ctypes.windll.LoadLibrary(os.path.abspath(dll_name))
        except Exception as e:
            try:
                # 尝试加载当前目录
                self.lib = ctypes.windll.LoadLibrary("CH341DLLA64.DLL")
            except:
                raise RuntimeError(f"无法加载 DLL，请检查路径: {e}")

        self.dev_index = 0
        self.lock = threading.Lock()

    def open(self):
        """打开设备并配置为 SPI 模式"""
        if self.lib.CH341OpenDevice(self.dev_index) <= 0:
            return False
        # 0x80 = SPI Mode, MSB First (虽然我们要发LSB，但通过软件翻转实现)
        self.lib.CH341SetStream(self.dev_index, 0x80)
        return True

    def close(self):
        if self.lib:
            self.lib.CH341CloseDevice(self.dev_index)

    def _reverse_byte(self, b):
        """PT6315 需要 LSB First，CH341A 发送 MSB，需软件翻转"""
        return int('{:08b}'.format(b)[::-1], 2)

    def send_data(self, data_list):
        """发送数据列表 (int list)"""
        reversed_data = [self._reverse_byte(b) for b in data_list]
        c_buf = (c_ubyte * len(reversed_data))(*reversed_data)

        with self.lock:
            # 0x80 = SPI模式, 自动片选
            self.lib.CH341StreamSPI4(self.dev_index, 0x80, len(c_buf), c_buf)