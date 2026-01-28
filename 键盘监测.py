import time
import threading
from collections import deque
from spi_comm import SPIAdapter
from vfd_driver import VFDScreen
from keyboard_monitor import KeyboardListener

# ================= 配置 =================
# 逻辑档位 0-8
BRIGHT_MAX = 8
BRIGHT_MIN = 1

# 物理 Grid 定义
GRID_CURSOR = 6
# 修改点：反转顺序。
# 假设 Grid 0 是最左边，Grid 5 是最右边
# 现在顺序定义为从右(5)到左(0)
GRID_TEXT_ORDER = [5, 4, 3, 2, 1, 0]

# 动画参数
IDLE_TIMEOUT = 0.5
STEP_DELAY = 0.2
BLINK_SPEED = 0.1


class QuarterDimController:
    def __init__(self):
        # 初始化硬件连接
        self.spi = SPIAdapter()
        if not self.spi.open():
            raise Exception("CH341 Device Open Failed")

        self.vfd = VFDScreen(self.spi)
        self.vfd.init_device()

        # 文本缓冲区，maxlen=6 对应 6 个字符位
        self.text_buffer = deque([' '] * 6, maxlen=6)
        self.running = True
        self.lock = threading.Lock()

        # 初始亮度状态
        self.current_brightness = BRIGHT_MAX
        self.set_hw_brightness(BRIGHT_MAX)

        self.last_input_time = time.time()
        self.is_animating = False

        # Grid 6 (光标/小图标) 的像素数据
        self.G6_ON = [0xFF, 0xFF, 0xFF]
        self.G6_OFF = [0x00, 0x00, 0x00]

    def set_hw_brightness(self, logic_level):
        """
        将逻辑档位(0-8) 映射到 VFD 硬件指令
        """
        logic_level = int(max(0, min(8, logic_level)))

        if logic_level == 0:
            cmd = 0x80  # Display OFF
        else:
            # 映射 1-8 到 0x88-0x8F (亮度级别)
            hw_val = logic_level - 1
            cmd = 0x88 + hw_val

        self.spi.send_data([cmd])
        self.current_brightness = logic_level

    def update_screen(self, text_list, cursor_on=True):
        """
        刷新屏幕显示内容
        """
        payload = [0xC0]  # 设置起始地址命令
        grid_data = {}

        # 处理光标 Grid
        grid_data[GRID_CURSOR] = self.G6_ON if cursor_on else self.G6_OFF

        # 核心逻辑：按照[5,4,3,2,1,0]的顺序填充字符
        # text_list[0] 是最新的字符，会被放在 GRID_TEXT_ORDER[0] (即物理 Grid 5，最右侧)
        for i, grid_id in enumerate(GRID_TEXT_ORDER):
            if i < len(text_list):
                char = text_list[i]
                grid_data[grid_id] = self.vfd.get_char_bytes(char)

        # 构造完整的 10 个 Grid 数据包 (每个 Grid 3 字节)
        for grid_id in range(10):
            payload.extend(grid_data.get(grid_id, [0, 0, 0]))

        self.spi.send_data(payload)

    def on_key(self, char):
        """
        按键回调函数
        """
        if char is None:
            self.running = False
            return

        with self.lock:
            self.is_animating = True
            self.last_input_time = time.time()

            # 唤醒：如果处于暗光状态，立刻拉满亮度
            if self.current_brightness < BRIGHT_MAX:
                self.set_hw_brightness(BRIGHT_MAX)

            # 将新字符推入左侧，旧字符向右移（但在反转的Grid顺序下，视觉上是向左移）
            self.text_buffer.appendleft(char)
            current_text = list(self.text_buffer)

            # 闪烁反馈效果
            self.update_screen(current_text, cursor_on=False)
            time.sleep(BLINK_SPEED)
            self.update_screen(current_text, cursor_on=True)

            self.is_animating = False
            self.last_input_time = time.time()

    def _dimming_loop(self):
        """
        后台线程：负责在无操作时逐级降低亮度
        """
        while self.running:
            now = time.time()
            idle_duration = now - self.last_input_time

            if not self.is_animating and idle_duration > IDLE_TIMEOUT:
                if self.current_brightness > BRIGHT_MIN:
                    with self.lock:
                        new_level = self.current_brightness - 1
                        self.set_hw_brightness(new_level)
                    time.sleep(STEP_DELAY)
                else:
                    time.sleep(0.5)
            else:
                time.sleep(0.1)

    def run(self):
        # 启动键盘监听
        kb = KeyboardListener(self.on_key)
        kb.start()

        # 启动自动变暗线程
        dim_thread = threading.Thread(target=self._dimming_loop, daemon=True)
        dim_thread.start()

        # 初始显示
        self.update_screen(list(self.text_buffer), cursor_on=True)
        # 初始设为最低亮度（测试唤醒）
        self.set_hw_brightness(BRIGHT_MIN)

        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                # 检测到 Ctrl+C 时什么都不做，继续循环
                pass

if __name__ == "__main__":
    app = QuarterDimController()
    app.run()