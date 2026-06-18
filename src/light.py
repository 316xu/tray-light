import pystray
from PIL import Image, ImageDraw, ImageFont
import threading
import sys
import time
import socket

try:
    from plyer import notification
    _notify = True
except Exception:
    _notify = False

PORT = 18765
COLORS = {
    "red":    {"fill": "red",           "outline": "darkred",       "count": 0},
    "green":  {"fill": "green",         "outline": "darkgreen",     "count": 0},
    "yellow": {"fill": "gold",          "outline": "darkgoldenrod", "count": 0},
}

cycle_index = 0
lock = threading.Lock()

def create_icon_image(number, fill_color, outline_color):
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=fill_color,
        outline=outline_color,
        width=2,
    )

    text = str(number)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2
    y = (size - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill="white", font=font)

    return image

def get_active_colors():
    return [(name, info) for name, info in COLORS.items() if info["count"] >= 1]

def update_icon(icon):
    global cycle_index
    active = get_active_colors()
    if not active:
        icon.icon = create_icon_image(0, "gray", "darkgray")
        icon.title = "等待信号..."
        return
    name, info = active[cycle_index % len(active)]
    icon.icon = create_icon_image(info["count"], info["fill"], info["outline"])
    icon.title = f"{name}: {info['count']}"

def show_notification(title, message):
    if _notify:
        try:
            notification.notify(title=title, message=message, timeout=3)
        except Exception:
            pass

def handle_signal(line):
    with lock:
        if line in COLORS:
            COLORS[line]["count"] += 1
            new_count = COLORS[line]["count"]
            show_notification("tray-light", f"{line}: +1 (当前 {new_count})")
            return True
        if line.startswith("-") and line[1:] in COLORS:
            color = line[1:]
            if COLORS[color]["count"] > 0:
                COLORS[color]["count"] -= 1
            new_count = COLORS[color]["count"]
            show_notification("tray-light", f"{color}: -1 (当前 {new_count})")
            return True
    return False

def tcp_server(icon):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", PORT))
    server.listen()
    while True:
        conn, _ = server.accept()
        data = conn.recv(1024)
        if data:
            line = data.decode().strip().lower()
            if handle_signal(line):
                update_icon(icon)
        conn.close()

def cycling_loop(icon):
    global cycle_index
    while True:
        time.sleep(2)
        with lock:
            active = get_active_colors()
            if len(active) >= 2:
                cycle_index = (cycle_index + 1) % len(active)
        update_icon(icon)

def send_signal(color):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("localhost", PORT))
        s.send(color.encode())
        s.close()
        op = "减少" if color.startswith("-") else "增加"
        print(f"已发送信号: {op} {color.lstrip('-')}")
    except ConnectionRefusedError:
        print("错误: 托盘程序未运行")
        sys.exit(1)

def on_reset(icon, item):
    with lock:
        for info in COLORS.values():
            info["count"] = 0
    update_icon(icon)

def on_exit(icon, item):
    icon.stop()

def main():
    image = create_icon_image(0, "gray", "darkgray")

    icon = pystray.Icon(
        name="signal_light",
        icon=image,
        title="Signal Light",
        menu=pystray.Menu(
            pystray.MenuItem("全部清零", on_reset, default=True),
            pystray.MenuItem("退出", on_exit),
        ),
    )

    threading.Thread(target=tcp_server, args=(icon,), daemon=True).start()
    threading.Thread(target=cycling_loop, args=(icon,), daemon=True).start()

    icon.run()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in COLORS or (arg.startswith("-") and arg[1:] in COLORS):
            send_signal(arg)
        else:
            print(f"用法: python {__file__} [{'/'.join(COLORS)}]")
            print(f"      python {__file__} -<color>   # 减少计数")
    else:
        main()
