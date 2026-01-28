import ctypes
import os
import sys
import time

# --- 配置部分 ---
# DLL 文件名，请确保该文件在当前目录下
DLL_PATH = r'CH341DLLA64.DLL'

# --- 加载 DLL ---
try:
    # 加载当前目录下的 DLL
    ch341_dll = ctypes.windll.LoadLibrary(os.path.abspath(DLL_PATH))
except FileNotFoundError:
    print(f"❌ 错误: 找不到 {DLL_PATH}。请确保 DLL 文件与脚本在同一目录下。")
    sys.exit(1)
except OSError as e:
    print(f"❌ 错误: 无法加载 DLL。通常是因为 Python 位数(32/64)与 DLL 位数不匹配。")
    print(f"系统报错信息: {e}")
    sys.exit(1)


def spi_loopback_test():
    print(f"--- CH341A SPI 回环测试 ---")

    # 1. 打开设备 (设备索引 0)
    # CH341OpenDevice 返回句柄，如果失败通常返回 -1 或 0 (视版本而定)
    dev_index = 0
    handle = ch341_dll.CH341OpenDevice(dev_index)

    if handle == -1 or handle == 0:
        print("❌ 无法打开设备。请检查：")
        print("1. USB 是否插好？")
        print("2. 驱动是否已安装？")
        print("3. 跳线帽是否在 I2C/SPI 模式？")
        return

    try:
        print("✅ 设备已打开")

        # 2. 配置 SPI 模式
        # CH341SetStream(index, mode)
        # mode=0x80: 设置为 SPI 模式 (默认 MSB first)
        if not ch341_dll.CH341SetStream(dev_index, 0x80):
            print("❌ 配置 SPI 模式失败")
            return

        # 3. 准备数据
        # 这里的 Buffer 是既作为发送，也作为接收 (In-place replace)
        message = b"Hello CH341A"
        buffer_len = len(message)

        # 创建一个可变的 C 字符缓冲区
        io_buffer = ctypes.create_string_buffer(message, buffer_len)

        print(f"📤 发送数据: {message}")
        print(f"   (Hex: {message.hex()})")

        # 4. 执行 SPI 传输 (4线模式)
        # CH341StreamSPI4(index, chip_select, length, buffer)
        # chip_select: 0x80 通常表示片选 CS0 低电平有效，传输完拉高
        # io_buffer: 发送的数据会被接收到的数据覆盖
        if ch341_dll.CH341StreamSPI4(dev_index, 0x80, buffer_len, io_buffer):

            # 读取缓冲区中的新数据
            received_data = io_buffer.raw

            print(f"📥 接收数据: {received_data}")
            print(f"   (Hex: {received_data.hex()})")

            # 5. 验证
            if received_data == message:
                print("\n✅ 测试通过！MISO 与 MOSI 连接正常。")
            else:
                if received_data == b'\xff' * buffer_len:
                    print("\n⚠️ 收到全 FF。通常表示 MISO 悬空（未连接到 MOSI）。")
                elif received_data == b'\x00' * buffer_len:
                    print("\n⚠️ 收到全 00。请检查接线。")
                else:
                    print("\n❌ 数据不一致，通信存在误码。")
        else:
            print("❌ SPI 传输函数调用失败")

    finally:
        # 6. 关闭设备
        ch341_dll.CH341CloseDevice(dev_index)
        print("--- 设备已关闭 ---")


if __name__ == "__main__":
    spi_loopback_test()