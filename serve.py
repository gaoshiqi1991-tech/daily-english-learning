"""局域网静态服务：让 Kindle 通过家里 Wi-Fi 直接打开每日页面。

用法：
    .venv\Scripts\python serve.py            # 默认 8000 端口
    .venv\Scripts\python serve.py --port 9000

启动后会打印局域网地址，例如：
    电脑版   http://192.168.1.6:8000/
    Kindle版 http://192.168.1.6:8000/kindle.html   <-- 在 Kindle 浏览器输入这个

注意：
- 电脑和 Kindle 必须连同一个 Wi-Fi；
- 首次运行 Windows 防火墙弹窗请选“允许”；
- 搭配 Windows 计划任务：DailyEnglish-Generate 每天生成页面，
  DailyEnglish-Server 开机自动启动本服务。
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socket
from pathlib import Path

import yaml


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("223.5.5.5", 80))  # 阿里 DNS，不真正发包，只为选网卡
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """pythonw 下 sys.stderr 为 None，默认日志会让每个请求崩溃；
    改为写日志文件，失败则静默。"""

    def log_message(self, fmt, *args):
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/server.log", "a", encoding="utf-8") as f:
                f.write("%s - %s\n" % (self.address_string(), fmt % args))
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    with open("config.yaml", "r", encoding="utf-8") as f:
        out_dir = Path(yaml.safe_load(f)["paths"]["output_dir"])
    handler = functools.partial(QuietHandler, directory=str(out_dir))
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    ip = lan_ip()
    print(f"[serve] 电脑版    http://{ip}:{args.port}/")
    print(f"[serve] Kindle版  http://{ip}:{args.port}/kindle.html")
    print("[serve] Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] 已停止")


if __name__ == "__main__":
    main()
