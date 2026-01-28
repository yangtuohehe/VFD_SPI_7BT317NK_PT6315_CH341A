# import time
# import os
# import ctypes
# import threading
# from ctypes import c_ubyte
#
#
# # ==========================================
# # 1. 驱动适配层 (保持你的核心逻辑)
# # ==========================================
# class SPIAdapter:
#     def __init__(self, dll_name=r'CH341DLLA64.DLL'):
#         try:
#             self.lib = ctypes.windll.LoadLibrary(os.path.abspath(dll_name))
#         except Exception as e:
#             raise RuntimeError(f"无法加载 DLL: {e}")
#         self.dev_index = 0
#         self.lock = threading.Lock()
#
#     def open(self):
#         if self.lib.CH341OpenDevice(self.dev_index) <= 0: return False
#         self.lib.CH341SetStream(self.dev_index, 0x80)
#         return True
#
#     def close(self):
#         self.lib.CH341CloseDevice(self.dev_index)
#
#     def _reverse_byte(self, b):
#         return int('{:08b}'.format(b)[::-1], 2)
#
#     def send_data(self, data_list):
#         reversed_data = [self._reverse_byte(b) for b in data_list]
#         c_buf = (c_ubyte * len(reversed_data))(*reversed_data)
#         with self.lock:
#             self.lib.CH341StreamSPI4(self.dev_index, 0x80, len(c_buf), c_buf)
#
#
# # ==========================================
# # 2. 深度扫描控制类
# # ==========================================
# class VFDScanner:
#     def __init__(self, spi):
#         self.spi = spi
#
#     def init_display(self):
#         """初始化 PT6315 到扫描模式"""
#         time.sleep(0.1)
#         self.spi.send_data([0x06])  # 设置为最大网格模式 (10 Grids / 12 Grids)
#         self.spi.send_data([0x44])  # 关键：设置为固定地址模式 (Fixed Address)，方便逐个扫描
#         self.spi.send_data([0x8F])  # 打开显示，最大亮度
#
#     def clear_all(self):
#         """清空所有 48 字节显存"""
#         self.spi.send_data([0x40])  # 临时切回地址自动增模式
#         payload = [0xC0] + [0x00] * 48
#         self.spi.send_data(payload)
#         self.spi.send_data([0x44])  # 切回固定地址模式
#
#     def test_bit(self, addr, bit_index):
#         """在指定地址点亮特定的位"""
#         val = 1 << bit_index
#         # 指令包：[地址字节, 数据字节]
#         self.spi.send_data([addr, val])
#
#
# def run_deep_scan():
#     print("========================================")
#     print("       PT6315 显存全地址深度扫描器       ")
#     print("========================================")
#
#     spi = SPIAdapter()
#     if not spi.open():
#         print("错误：无法连接设备")
#         return
#
#     scanner = VFDScanner(spi)
#     scanner.init_display()
#
#     # PT6315 显存地址范围通常是 0xC0 到 0xEF (共 48 字节)
#     # 每个地址对应 8 个 Segment
#     # start_addr = 0xC0
#     # end_addr = 0xEF
#     start_addr = 0xd2
#     end_addr = 0xd2
#
#     try:
#         print(f"开始扫描范围: {hex(start_addr)} -> {hex(end_addr)}")
#         print("操作提示: [回车]-下一个位 | [a]-上一个位 | [r]-重走当前位 | [q]-退出")
#
#         current_addr = start_addr
#         while current_addr <= end_addr:
#             for bit in range(8):
#                 scanner.clear_all()  # 先清空防止干扰
#                 scanner.test_bit(current_addr, bit)
#
#                 print(f"\r正在测试: 地址 {hex(current_addr)} | Bit {bit} (掩码: {hex(1 << bit)})", end="")
#
#                 cmd = input().lower()
#                 if cmd == 'q':
#                     return
#                 elif cmd == 'a':
#                     # 这里逻辑简单处理，实际使用建议微调
#                     print("\n回退一步...")
#                     break
#                 elif cmd == 'r':
#                     # 重测逻辑
#                     continue
#
#             current_addr += 1
#             print(f"\n--- 切换到地址 {hex(current_addr)} ---")
#
#     except KeyboardInterrupt:
#         pass
#     finally:
#         scanner.clear_all()
#         spi.close()
#         print("\n扫描任务已关闭。")
#
#
# if __name__ == "__main__":
#     run_deep_scan()

import time
import os
import ctypes
import threading
from ctypes import c_ubyte


# ==========================================
# 1. 驱动适配层
# ==========================================
class SPIAdapter:
    def __init__(self, dll_name=r'CH341DLLA64.DLL'):
        try:
            self.lib = ctypes.windll.LoadLibrary(os.path.abspath(dll_name))
        except Exception as e:
            raise RuntimeError(f"无法加载 DLL: {e}")
        self.dev_index = 0
        self.lock = threading.Lock()

    def open(self):
        if self.lib.CH341OpenDevice(self.dev_index) <= 0: return False
        self.lib.CH341SetStream(self.dev_index, 0x80)
        return True

    def close(self):
        self.lib.CH341CloseDevice(self.dev_index)

    def _reverse_byte(self, b):
        return int('{:08b}'.format(b)[::-1], 2)

    def send_data(self, data_list):
        reversed_data = [self._reverse_byte(b) for b in data_list]
        c_buf = (c_ubyte * len(reversed_data))(*reversed_data)
        with self.lock:
            self.lib.CH341StreamSPI4(self.dev_index, 0x80, len(c_buf), c_buf)


# ==========================================
# 2. 组合测试逻辑
# ==========================================
def run_combination_test():
    target_addr = 0xD2  # 你指定的地址

    spi = SPIAdapter()
    if not spi.open():
        print("无法打开设备")
        return

    print(f"=== 正在针对地址 {hex(target_addr)} 进行组合测试 ===")
    print("模式说明:")
    print("1. 输入 hex 值 (如 FF) 直接点亮对应组合")
    print("2. 输入 'auto' 开始从 00 到 FF 自动循环扫描")
    print("3. 输入 'q' 退出")
    print("-" * 40)

    try:
        # 初始化 PT6315 (固定地址模式)
        spi.send_data([0x06])  # 10 Grids
        spi.send_data([0x44])  # 固定地址模式
        spi.send_data([0x8F])  # 开启显示

        while True:
            user_in = input(f"请输入地址 {hex(target_addr)} 的测试值 (Hex): ").strip().lower()

            if user_in == 'q':
                break

            elif user_in == 'auto':
                print("进入自动扫描模式 (间隔 0.5s)... 按 Ctrl+C 停止自动扫描")
                try:
                    for val in range(256):
                        print(f"\r当前值: {hex(val)} (二进制: {bin(val)[2:].zfill(8)})", end="")
                        spi.send_data([target_addr, val])
                        time.sleep(0.5)
                    print("\n自动扫描完成。")
                except KeyboardInterrupt:
                    print("\n已停止自动扫描。")
                continue

            try:
                # 将用户输入的 hex 字符串转为整数
                val = int(user_in, 16)
                if 0 <= val <= 255:
                    spi.send_data([target_addr, val])
                    print(f"已发送 {hex(val)} -> 二进制: {bin(val)[2:].zfill(8)}")
                else:
                    print("错误: 请输入 00 到 FF 之间的值")
            except ValueError:
                if user_in != '':
                    print("错误: 无效的 Hex 输入")

    finally:
        # 清空测试地址并关闭
        spi.send_data([target_addr, 0x00])
        spi.close()
        print("测试结束。")


if __name__ == "__main__":
    run_combination_test()