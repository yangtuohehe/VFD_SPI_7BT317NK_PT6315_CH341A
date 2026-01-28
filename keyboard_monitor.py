import keyboard
import threading
import time


class KeyboardListener:
    def __init__(self, callback_func):
        """
        :param callback_func: 接收字符的回调函数
        """
        self.callback = callback_func
        self.running = False
        # keyboard 库不需要循环线程，它有自己的钩子，但为了保持架构一致，
        # 我们还是保留 start/stop 的接口形式
        self.hook = None

    def _on_key_event(self, event):
        """内部事件处理"""
        if not self.running:
            return

        # event.name 获取按键名
        key_name = event.name

        # 过滤：只处理按键按下(down)且不是释放(up)
        if event.event_type == 'down':

            # 处理 ESC
            if key_name == 'esc':
                self.callback(None)
                return

            # 处理普通字符
            # 这里的逻辑是：如果是字母且长度为1，直接返回
            # 如果是 space, enter 等特殊键，也可以处理
            if len(key_name) == 1:
                self.callback(key_name)
            elif key_name == 'space':
                self.callback(' ')

    def start(self):
        self.running = True
        # 建立钩子，监听所有按键
        self.hook = keyboard.hook(self._on_key_event)
        print("[Keyboard] 监听已启动 (全局模式，窗口后台也能用)")

    def stop(self):
        self.running = False
        if self.hook:
            keyboard.unhook_all()
        print("[Keyboard] 监听已停止")


# ==========================================
# 👇 测试代码 👇
# ==========================================
if __name__ == "__main__":
    def test_callback(char):
        if char is None:
            print("\n[Test] 检测到 ESC，退出！")
            global is_testing
            is_testing = False
        else:
            print(f"[Test] 按键: {char}")


    print("--- 键盘监听测试 (Keyboard库版) ---")
    print("请按键 (支持后台输入)... 按 ESC 退出")

    listener = KeyboardListener(test_callback)
    listener.start()

    is_testing = True
    try:
        while is_testing:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()