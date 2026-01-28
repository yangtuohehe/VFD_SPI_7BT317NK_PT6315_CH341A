import ctypes
import os
import sys

# ================= 配置区 =================
# 根据你的测试结果已锁定：
GRID_SPECIAL = 6  # 物理第1屏 (特殊符号)
GRID_DIGIT = 0  # 物理第2屏 (标准数字)
# ==========================================

DLL_PATH = r'C:\Users\xz\Desktop\资料\CH341PAR\CH341PAR\CH341DLLA64.DLL'
try:
    ch341 = ctypes.windll.LoadLibrary(os.path.abspath(DLL_PATH))
except:
    sys.exit("找不到 DLL")


def reverse_byte(b):
    return int('{:08b}'.format(b)[::-1], 2)


def send_spi(dev_index, data_list):
    reversed_data = [reverse_byte(b) for b in data_list]
    io_buffer = ctypes.create_string_buffer(bytes(reversed_data), len(reversed_data))
    ch341.CH341StreamSPI4(dev_index, 0x80, len(reversed_data), io_buffer)


def scan_target(dev_index, grid_id, name):
    print(f"\n========================================")
    print(f"👁️  正在扫描: {name} (逻辑 ID: {grid_id})")
    print(f"========================================")

    # 遍历 3 个字节 (Byte 0, 1, 2)
    for byte_idx in range(3):
        # 遍历 8 个位 (Bit 0-7)
        for bit_idx in range(8):

            # 构造数据
            pixel_val = (1 << bit_idx)

            # 构造全屏 Payload (10 Grids)
            payload = [0xC0]
            for i in range(10):
                if i == grid_id:
                    # 点亮目标
                    grid_data = [0x00, 0x00, 0x00]
                    grid_data[byte_idx] = pixel_val
                    payload.extend(grid_data)
                else:
                    # 其他全灭
                    payload.extend([0x00, 0x00, 0x00])

            send_spi(dev_index, payload)

            # 打印并等待
            print(f"👉 Byte {byte_idx} | Bit {bit_idx} (Hex: {hex(pixel_val)})")
            user_input = input("   [按回车下一个, q 退出]: ")
            if user_input.lower() == 'q':
                return False
    return True


def main():
    dev_index = 0
    if ch341.CH341OpenDevice(dev_index) <= 0:
        print("无法打开设备")
        return

    ch341.CH341SetStream(dev_index, 0x80)
    send_spi(dev_index, [0x06])  # Mode 10
    send_spi(dev_index, [0x40])  # Write Data
    send_spi(dev_index, [0x8F])  # Display ON

    try:
        # 1. 扫描特殊屏 (Grid 6)
        print("📝 第一阶段：记录特殊符号 (DVD, MP3, 圈圈等)")
        if not scan_target(dev_index, GRID_SPECIAL, "物理第1屏 (Grid 6)"):
            return

        print("\n✅ 特殊屏扫描完毕！")
        input("   >>> 按回车键开始扫描数字屏 (Grid 0) <<<")

        # 2. 扫描数字屏 (Grid 0)
        print("\n📝 第二阶段：记录数字笔画 (a, b, c, d, e, f, g)")
        # 提示：对照标准数码管结构记录
        #      a
        #    f   b
        #      g
        #    e   c
        #      d
        scan_target(dev_index, GRID_DIGIT, "物理第2屏 (Grid 0)")

        print("\n🎉 全部扫描结束！")
        send_spi(dev_index, [0xC0] + [0x00] * 30)  # 清屏

    finally:
        ch341.CH341CloseDevice(dev_index)


if __name__ == "__main__":
    main()