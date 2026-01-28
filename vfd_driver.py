
# ================= 字库定义 =================
FONTS = {
    '!': 0x202204, '"': 0x300000, '#': 0x505700, '$': 0x2fa70f, '%': 0x451209,
    '&': 0x1bca0f, "'": 0x100000, '(': 0x090807, ')': 0x84800e, '*': 0x707700,
    '+': 0x202700, ',': 0x008000, '-': 0x000700, '.': 0x000008, '/': 0x441201,
    '0': 0xcf980f, '1': 0x848008, '2': 0x870f0f, '3': 0x47870f, '4': 0x8d8708,
    '5': 0x0f870f, '6': 0x0f8f0f, '7': 0x8f8008, '8': 0x8f8f0f, '9': 0x8f870f,
    ':': 0x202000, ';': 0x202001, '<': 0x404100, '=': 0x07000f, '>': 0x101200,
    '?': 0x472204, '@': 0x8f1f07,
    'A': 0x8f8f09, 'B': 0xa7a60f, 'C': 0x0f080f, 'D': 0xa7a20f, 'E': 0x0f0f0f,
    'F': 0x0f0f01, 'G': 0x0f8c0f, 'H': 0x8d8f09, 'I': 0x27220f, 'J': 0x222a05,
    'K': 0x4d4b09, 'L': 0x09080f, 'M': 0xdd8a09, 'N': 0x9dca09, 'O': 0x8f880f,
    'P': 0x8f0f01, 'Q': 0x8fc80f, 'R': 0x8f4f09, 'S': 0x0f870f, 'T': 0x272204,
    'U': 0x8d880f, 'V': 0x552200, 'W': 0x8dda09, 'X': 0x555209, 'Y': 0x552204,
    'Z': 0x47120f,
    '[': 0x0f080f, '\\': 0x114208, ']': 0x87800f, '^': 0x205000, '_': 0x00000f,
    '`': 0x100000, ' ': 0x000000
}

# --- 动态生成频谱字库 (0-10) ---
# 定义每一格对应的位
SEGMENTS_ORDER = [
    0x000800, 0x001000, 0x002000, 0x004000, 0x008000,  # 1-5 格
    0x080000, 0x100000, 0x200000, 0x400000, 0x800000  # 6-10 格
]

SPECTRUM_FONTS = {0: 0x000000}
current_code = 0x000000
for i, code in enumerate(SEGMENTS_ORDER):
    current_code |= code
    SPECTRUM_FONTS[i + 1] = current_code

# 将频谱字库合并入主字库 (Key为int类型，不会与Char冲突)
FONTS.update(SPECTRUM_FONTS)


class VFDScreen:
    def __init__(self, spi_adapter):
        self.spi = spi_adapter
        # Grid 6: 物理第1屏 (特殊符号)
        # Grid 0-5: 物理第2-7屏 (显示文本/频谱)
        self.grid_special = 6
        self.grids_text = [0, 1, 2, 3, 4, 5]

    def init_device(self):
        """初始化 PT6315"""
        self.spi.send_data([0x06])  # Mode: 10 Grids
        self.spi.send_data([0x40])  # Data: Write, Inc Addr
        self.spi.send_data([0x8F])  # Display ON, Max Bright

    def get_char_bytes(self, char_or_level):
        """获取单个字符或频谱等级的3字节数据"""
        if isinstance(char_or_level, int):
            # 处理频谱等级 (0-10)
            val = FONTS.get(char_or_level, 0x00)
        else:
            # 处理文字
            key = char_or_level.upper() if isinstance(char_or_level, str) else ' '
            val = FONTS.get(key, 0x00)

        return [(val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]

    def write_grid_fixed(self, grid_id, char_bytes):
        """[调试用] 单独写一个 Grid"""
        addr = 0xC0 + (grid_id * 3)
        self.spi.send_data([addr] + char_bytes)

    def display_spectrum(self, levels):
        """
        [频谱核心方法]
        一次性发送所有 Grid 的数据以保证帧率
        levels: list, 包含6个整数 (0-10)
        """
        payload = [0xC0]  # 起始地址

        # 遍历所有逻辑 Grid (0-9)
        for grid_id in range(10):
            if grid_id in self.grids_text:
                # 找到当前 Grid 对应的是第几列频谱
                idx = self.grids_text.index(grid_id)
                if idx < len(levels):
                    payload.extend(self.get_char_bytes(levels[idx]))
                else:
                    payload.extend([0, 0, 0])
            elif grid_id == self.grid_special:
                # 特殊符号屏常亮
                payload.extend([0xFF, 0xFF, 0xFF])
            else:
                # 其他未使用 Grid 全黑
                payload.extend([0, 0, 0])

        self.spi.send_data(payload)

    def clear(self):
        """清屏"""
        payload = [0xC0] + [0x00] * 48
        self.spi.send_data(payload)