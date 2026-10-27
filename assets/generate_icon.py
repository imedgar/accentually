"""
Generates a clean Windows ICO file for QuickAccent.
Creates an elegant 32x32 and 48x48 icon with an accented letter badge.
"""
import struct
import os

def generate_ico(output_path):
    sizes = [32, 48]
    images_data = []
    
    for size in sizes:
        # Create 32-bit RGBA bitmap data (BGRA format)
        pixels = bytearray(size * size * 4)
        center = size / 2.0
        radius = size * 0.44
        
        # Draw rounded square/circle badge
        for y in range(size):
            for x in range(size):
                idx = ((size - 1 - y) * size + x) * 4 # bottom-up
                dx = x - center
                dy = y - center
                dist = (dx * dx + dy * dy) ** 0.5
                
                # Outer smooth circle
                if dist <= radius:
                    # Windows blue gradient / accent color (#0078D4)
                    t = y / size
                    b = int(212 * (1 - 0.2 * t))
                    g = int(120 * (1 - 0.2 * t))
                    r = int(0)
                    a = 255
                    if dist > radius - 1.2:
                        a = int(255 * (radius - dist) / 1.2)
                    pixels[idx:idx+4] = bytearray([b, g, r, a])
                else:
                    pixels[idx:idx+4] = bytearray([0, 0, 0, 0])
        
        # Draw a macron accent bar on top (representing garumzīme / accent)
        bar_w = int(size * 0.44)
        bar_h = max(2, int(size * 0.09))
        bar_x0 = int((size - bar_w) / 2)
        bar_y0 = int(size * 0.22)
        for by in range(bar_y0, bar_y0 + bar_h):
            for bx in range(bar_x0, bar_x0 + bar_w):
                idx = ((size - 1 - by) * size + bx) * 4
                pixels[idx:idx+4] = bytearray([255, 255, 255, 255])
                
        # Draw an 'a' shaped glyph or arch below the bar
        arch_y0 = bar_y0 + bar_h + int(size * 0.08)
        arch_h = int(size * 0.38)
        arch_w = int(size * 0.38)
        arch_x0 = int((size - arch_w) / 2)
        stroke = max(2, int(size * 0.08))
        
        for ay in range(arch_y0, arch_y0 + arch_h):
            for ax in range(arch_x0, arch_x0 + arch_w):
                # Draw letter arch outline
                is_top = ay < arch_y0 + stroke
                is_right = ax >= arch_x0 + arch_w - stroke
                is_bottom = ay >= arch_y0 + arch_h - stroke
                is_left = (ax < arch_x0 + stroke) and (ay >= arch_y0 + arch_h / 2)
                is_cross = (ay >= arch_y0 + arch_h / 2) and (ay < arch_y0 + arch_h / 2 + stroke)
                
                if is_top or is_right or is_bottom or is_left or is_cross:
                    idx = ((size - 1 - ay) * size + ax) * 4
                    pixels[idx:idx+4] = bytearray([255, 255, 255, 255])
        
        # 1-bit mask (all zeros for 32-bit alpha)
        mask = bytearray((size * size + 7) // 8)
        
        # BITMAPINFOHEADER (40 bytes)
        bih = struct.pack('<IIIHHIIIIII', 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
        images_data.append((size, bih + pixels + mask))
    
    # Pack ICO directory header
    # ICONDIR: idReserved (0), idType (1 = icon), idCount (num images)
    icondir = struct.pack('<HHH', 0, 1, len(images_data))
    
    # Calculate offset for each image data
    offset = 6 + len(images_data) * 16
    direntries = []
    
    for size, data in images_data:
        # ICONDIRENTRY: width, height, colorCount, reserved, planes, bitCount, bytesInRes, offset
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entry = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(data), offset)
        direntries.append(entry)
        offset += len(data)
        
    with open(output_path, 'wb') as f:
        f.write(icondir)
        for entry in direntries:
            f.write(entry)
        for _, data in images_data:
            f.write(data)
            
    print(f"Icon generated at {output_path}")

if __name__ == '__main__':
    ico_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    generate_ico(ico_path)
