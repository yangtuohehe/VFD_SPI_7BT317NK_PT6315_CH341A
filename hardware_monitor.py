import psutil
import wmi
import pynvml
import time
import ctypes


class HardwareMonitor:
    def __init__(self):
        self.nvml_inited = False
        self.wmi_obj = None
        # 阻止系统在程序隐藏时进入低功耗状态 (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        except:
            pass

        self._init_nvml()
        self._init_wmi()

    def _init_nvml(self):
        """强制重新初始化 NVML"""
        try:
            pynvml.nvmlShutdown()  # 先尝试彻底关闭旧连接
        except:
            pass
        try:
            pynvml.nvmlInit()
            self.nvml_inited = True
        except Exception as e:
            self.nvml_inited = False

    def _init_wmi(self):
        try:
            # 重新建立 WMI 连接
            self.wmi_obj = wmi.WMI(namespace="root/wmi")
        except:
            self.wmi_obj = None

    def get_cpu_temp(self):
        if not self.wmi_obj:
            self._init_wmi()
        try:
            temps = self.wmi_obj.MSAcpi_ThermalZoneTemperature()
            for t in temps:
                c = int(t.CurrentTemperature / 10.0 - 273.15)
                if 0 < c < 120: return c
        except:
            self.wmi_obj = None  # 隐藏状态下如果读取失败，重置 WMI
        return 0

    def get_gpu_data(self):
        """专门针对后台运行优化的 GPU 读取"""
        if not self.nvml_inited:
            self._init_nvml()
            if not self.nvml_inited: return 0, 0

        try:
            # 每次读取都重新获取句柄，防止隐藏窗口导致的句柄失效
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu

            # 如果在后台读到了 0，通常是驱动进入了持久化模式丢失
            if temp == 0:
                self._init_nvml()
                return self.get_gpu_data()  # 递归尝试一次新连接

            return int(temp), int(util)
        except Exception:
            self.nvml_inited = False  # 标记失效
            return 0, 0

    def get_all_metrics(self):
        # 强制系统给当前线程提速
        gpu_temp, gpu_load = self.get_gpu_data()
        return {
            "CT": self.get_cpu_temp(),
            "GT": gpu_temp,
            "M": int(psutil.virtual_memory().percent),
            "G": gpu_load,
            "C": int(psutil.cpu_percent(interval=None))
        }