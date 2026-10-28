# -*- coding: utf-8 -*-
"""获客工作台 · serve.py
零依赖本地服务。用法：
    python serve.py            # 默认 8790 端口，先构建再服务
    python serve.py 8791       # 换端口
    python serve.py --no-build # 不重新构建，直接开
"""
import sys
import json
import shutil
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DATA = ROOT / "data"

# 写入白名单：字段名 -> 文件名（只允许这三个）
FILE_MAP = (("scripts", "scripts.json"), ("demands", "demands.json"), ("staff", "staff.json"))
RESET_FILES = ("works.json", "leads.json")
CSV_PATTERNS = ("works_*.csv", "inbox_*.csv", "replies_*.csv")


class NoCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *a):
        pass

    # ---------- 小工具 ----------
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _backup_data(self):
        """整个 data/ 备份一份，返回备份目录名"""
        ts = time.strftime("%Y%m%d_%H%M%S")
        bk = DATA / ("_backup_" + ts)
        bk.mkdir(parents=True, exist_ok=True)
        for f in DATA.glob("*"):
            if f.is_file():
                try:
                    shutil.copy2(f, bk / f.name)
                except Exception:
                    pass
        return bk.name

    # ---------- 本地写入接口（只给「行业包」页用） ----------
    def do_POST(self):
        if self.path.split("?")[0] != "/api/apply-industry":
            self._send_json({"ok": False, "error": "not found"}, 404)
            return

        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", ""):
            self._send_json({"ok": False, "error": "仅允许本机操作"}, 403)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            self._send_json({"ok": False, "error": "请求解析失败: %s" % e}, 400)
            return

        if not DATA.exists():
            self._send_json({"ok": False, "error": "data/ 目录不存在"}, 500)
            return

        try:
            backup = self._backup_data()
            written, removed, reset = [], [], []

            # ① 先写三个数据文件（字段名映射，白名单校验）
            for key, name in FILE_MAP:
                if key in payload and isinstance(payload[key], list) and payload[key]:
                    (DATA / name).write_text(
                        json.dumps(payload[key], ensure_ascii=False, indent=2),
                        encoding="utf-8")
                    written.append(name)

            # ★ 一个文件都没写成 → 直接报错，绝不动老数据
            if not written:
                self._send_json({
                    "ok": False,
                    "error": "没有收到可写入的数据（scripts/demands/staff 都是空的）。为保护现有数据，未做任何改动。",
                    "backup": backup,
                }, 400)
                return

            # ② 写入成功后，才清空作品/线索 + 删旧 CSV
            if payload.get("reset"):
                for name in RESET_FILES:
                    (DATA / name).write_text("[]", encoding="utf-8")
                    reset.append(name)
                for pat in CSV_PATTERNS:
                    for f in DATA.glob(pat):
                        if f.is_file():
                            f.unlink()
                            removed.append(f.name)

            sys.path.insert(0, str(ROOT))
            import build as _build
            import importlib
            importlib.reload(_build)
            _build.main()

            self._send_json({
                "ok": True,
                "industry": payload.get("industry", ""),
                "written": written,
                "reset": reset,
                "removed": removed,
                "backup": backup,
            })
        except Exception as e:
            self._send_json({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 500)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_build = "--no-build" in sys.argv
    port = int(args[0]) if args else 8790

    if not no_build:
        sys.path.insert(0, str(ROOT))
        import build
        build.main()

    SITE.mkdir(exist_ok=True)
    handler = partial(NoCache, directory=str(SITE))
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"\n  获客工作台已启动 →  http://127.0.0.1:{port}/")
    print(f"  按 Ctrl+C 停止\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
