import time
import os
import sys
import psutil
import ctypes
from vfd_driver import VFDScreen
from spi_comm import SPIAdapter
from hardware_monitor import HardwareMonitor

# ==========================================
# 1. 环境与权限保活设置
# ==========================================

# 锁定工作目录：确保打包成 EXE 后能找到同目录下的 DLL
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_path)


def optimize_process():
    """提升进程权限级别，防止后台运行时被系统挂起"""
    try:
        # 1. 设置进程为高优先级
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)

        # 2. 阻止系统在后台运行时进入节能模式 (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        # 这对于隐藏窗口运行至关重要
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        print("系统调度优化已开启：高优先级模式")
    except Exception as e:
        print(f"优化设置失败: {e}")


# ==========================================
# 2. VFD 显示逻辑类
# ==========================================

class CarouselVFDScreen(VFDScreen):
    def __init__(self, spi_adapter):
        super().__init__(spi_adapter)
        # 覆盖父类定义，确保包含物理第1到第7块 (Grid 0-6)
        self.grids_text = [0, 1, 2, 3, 4, 5, 6]

    def display_metrics(self, label, value, unit="%"):
        """
        左移紧凑布局：
        Grid 0-1: 标签 (如 CT)
        Grid 2-4: 数字 (左对齐)
        Grid 5:   单位 (如 C 或 %)
        Grid 6:   关闭 (留空)
        """
        # 处理数值：左对齐占 3 位，确保数字紧贴标签
        val_str = str(value).ljust(3)

        # 构造 7 个位置的显示列表
        display_list = [
            label[0],  # Grid 0
            label[1] if len(label) > 1 else " ",  # Grid 1
            val_str[0],  # Grid 2
            val_str[1],  # Grid 3
            val_str[2],  # Grid 4
            unit,  # Grid 5
            " "  # Grid 6 (原先单位的位置，现在空出来)
        ]

        payload = [0xC0]  # PT6315 起始显存地址

        for grid_id in range(10):
            if grid_id in self.grids_text:
                idx = self.grids_text.index(grid_id)
                char = display_list[idx]
                payload.extend(self.get_char_bytes(char))
            else:
                # 关闭其余所有 Grid（包括特殊符号位）
                payload.extend([0x00, 0x00, 0x00])

        self.spi.send_data(payload)


# ==========================================
# 3. 主程序入口
# ==========================================

def main():
    # 执行后台运行优化
    #optimize_process()

    try:
        # 1. 初始化硬件连接
        spi = SPIAdapter()
        if not spi.open():
            print("CRITICAL ERROR: 无法打开 CH341 设备，请检查驱动和连接！")
            input("按回车键退出...")
            return

        # 2. 初始化 VFD 屏幕
        vfd = CarouselVFDScreen(spi)
        vfd.init_device()
        vfd.clear()

        # 3. 延迟启动监测模块，给驱动留出唤醒时间
        print("正在初始化硬件监测模块...")
        time.sleep(1)
        monitor = HardwareMonitor()

        # 轮播序列配置：(显示标签, 数据Key, 单位)
        sequence = [
            ("CT", "CT", "C"),  # CPU Temp
            ("GT", "GT", "C"),  # GPU Temp
            ("MU", "M", "%"),  # Memory Usage
            ("GU", "G", "%"),  # GPU Usage
            ("CU", "C", "%")  # CPU Usage
        ]

        print("VFD 监控已就绪，开始后台运行...")

        while True:
            for label, key, unit in sequence:
                # 每次切换前抓取最新数据
                data = monitor.get_all_metrics()
                val = data.get(key, 0)

                # 更新屏幕显示
                vfd.display_metrics(label, val, unit)

                # 轮播停顿时间 (秒)
                time.sleep(3)

    except KeyboardInterrupt:
        print("\n用户中断，正在清理退出...")
        vfd.clear()
        spi.close()
    except Exception as e:
        print(f"\n运行时崩溃: {e}")
        # 崩溃时尝试关闭设备，防止 SPI 挂起
        try:
            spi.close()
        except:
            pass


if __name__ == "__main__":
    main()