"""
生成应用图标 (.ico)。

在 CI 环境或首次构建时运行，从内嵌的 PNG/SVG 生成 .ico 文件。
如果系统没有 PIL，则创建一个纯色占位图标（仍可正常使用）。
"""

import os
import struct
import zlib

ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
ICO_PATH = os.path.join(ICON_DIR, "icon.ico")
PNG_PATH = os.path.join(ICON_DIR, "icon.png")


def _create_png() -> bytes:
    """创建一个 32x32 的简单 PNG 图标（🧹 扫帚风格）。"""
    width, height = 32, 32
    # RGBA 像素数据（每个像素 4 字节）
    pixels = bytearray()

    for y in range(height):
        for x in range(width):
            # 画一个简单的扫帚图案
            cx, cy = x - 16, y - 16  # 中心偏移
            r, g, b, a = 0, 0, 0, 0  # 默认透明

            # 扫帚头（圆形，蓝色系）
            dist = (cx * cx + cy * cy) ** 0.5
            if 6 <= dist <= 12:
                # 渐变蓝
                t = (dist - 6) / 6
                r, g, b, a = int(50 + 100 * t), int(120 + 80 * (1 - t)), 200, 255
            elif dist < 6:
                r, g, b, a = 50, 120, 200, 255

            # 扫帚柄（竖线）
            if -2 <= cx <= 2 and (y < 8 or y > 24):
                r, g, b, a = 180, 150, 100, 255

            # 刷毛（底部斜线）
            if y >= 22 and abs(cx) <= 8 - (y - 22) * 0.5:
                r, g, b, a = 200, 180, 120, 255

            pixels.extend([r, g, b, a])

    # 构建 PNG
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    # IDAT (raw pixel data)
    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter byte
        for x in range(width):
            i = (y * width + x) * 4
            raw += bytes(pixels[i : i + 4])
    compressed = zlib.compress(raw)
    # IEND
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


def _png_to_ico(png_data: bytes) -> bytes:
    """将 PNG 包装为 ICO 格式。"""
    # ICO header
    ico = struct.pack("<HHH", 0, 1, 1)  # reserved, type=1(icon), count=1
    # Directory entry
    w, h = 32, 32
    if w >= 256:
        w = 0
    if h >= 256:
        h = 0
    ico += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_data), 22)
    # PNG data
    ico += png_data
    return ico


def main():
    os.makedirs(ICON_DIR, exist_ok=True)

    png_data = _create_png()
    with open(PNG_PATH, "wb") as f:
        f.write(png_data)
    print(f"  ✓ PNG icon: {PNG_PATH} ({len(png_data)} bytes)")

    ico_data = _png_to_ico(png_data)
    with open(ICO_PATH, "wb") as f:
        f.write(ico_data)
    print(f"  ✓ ICO icon: {ICO_PATH} ({len(ico_data)} bytes)")


if __name__ == "__main__":
    main()
