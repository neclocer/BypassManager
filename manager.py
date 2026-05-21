
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import zipfile
import shutil
from pathlib import Path

APP_VERSION    = "1.0.0"
UPDATE_HOST    = "https://neclocer.tech/bypass"

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).resolve().parent
else:
    BASE = Path(__file__).resolve().parent

ZAPRET    = BASE / "zapret"
TGPROXY   = BASE / "tg_proxy"
WINWS_EXE = ZAPRET / "bin" / "winws.exe"
LISTS_DIR = ZAPRET / "lists"

_zapret_proc  = None
_tg_proc      = None
_tg_thread    = None
_tg_stop      = threading.Event()
_PREFS_FILE = BASE / "bypass_prefs.txt"

def _load_prefs():
    global _selected_bat
    try:
        if _PREFS_FILE.exists():
            val = _PREFS_FILE.read_text(encoding="utf-8").strip()
            if val:
                _selected_bat = val
    except Exception:
        pass

def _save_prefs():
    try:
        _PREFS_FILE.write_text(_selected_bat, encoding="utf-8")
    except Exception:
        pass

_selected_bat = "general.bat"
_tg_secret: str = ""
_load_prefs()

def _get_or_create_secret() -> str:
    
    global _tg_secret
    secret_file = BASE / "tg_secret.txt"
    if secret_file.exists():
        _tg_secret = secret_file.read_text(encoding="utf-8").strip()
        if _tg_secret:
            return _tg_secret
    import os as _os
    _tg_secret = _os.urandom(16).hex()
    secret_file.write_text(_tg_secret, encoding="utf-8")
    return _tg_secret

def get_bat_options() -> dict[str, str]:
    
    if not ZAPRET.exists():
        return {"Стандартный": "general.bat"}
    bats = sorted(ZAPRET.glob("general*.bat"))
    result = {}
    for b in bats:
        name = b.stem
        if name == "general":
            label = "Стандартный"
        else:
            label = name.replace("general ", "").strip("()")
        result[label] = b.name
    return result if result else {"Стандартный": "general.bat"}

def zapret_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq winws.exe", "/NH"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stderr=subprocess.DEVNULL,
        ).decode("cp866", errors="ignore")
        return "winws.exe" in out
    except Exception:
        return False

def zapret_start():
    global _zapret_proc
    if zapret_running():
        return True, ""
    if not WINWS_EXE.exists():
        return False, f"Не найден winws.exe:\n{WINWS_EXE}"
    bat = ZAPRET / _selected_bat
    if not bat.exists():
        return False, f"Не найден файл:\n{bat}"
    try:
        _zapret_proc = subprocess.Popen(
            ["cmd.exe", "/c", str(bat)],
            cwd=str(ZAPRET),
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        time.sleep(2)
        if zapret_running():
            return True, ""
        return False, "winws.exe запустился, но сразу завершился.\nПопробуй другой вариант (ALT, ALT2 и т.д.)"
    except Exception as e:
        return False, str(e)

def zapret_stop():
    global _zapret_proc
    subprocess.run(["taskkill", "/F", "/IM", "winws.exe"],
                   creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True)
    if _zapret_proc:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(_zapret_proc.pid)],
                           creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True)
        except Exception:
            pass
        _zapret_proc = None

ZAPRET_RELEASES     = "https://github.com/Flowseal/zapret-discord-youtube/releases/latest"
ZAPRET_ASSETS_URL   = "https://github.com/Flowseal/zapret-discord-youtube/releases/expanded_assets/{tag}"

def check_zapret_update():
    
    try:
        import re
        try:
            req = urllib.request.Request(
                f"{UPDATE_HOST}/zapret_version.txt",
                headers={"User-Agent": "BypassManager"}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                remote_ver = r.read().decode().strip()
            ver_file = ZAPRET / ".service" / "version.txt"
            current = ver_file.read_text().strip() if ver_file.exists() else ""
            print(f"[version] remote={repr(remote_ver)} local={repr(current)}")
            if remote_ver and remote_ver != current:
                return remote_ver, f"{UPDATE_HOST}/zapret.zip"
            return None, None
        except Exception:
            pass

        req = urllib.request.Request(
            ZAPRET_RELEASES,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            final_url = r.geturl()
        tag = final_url.rstrip("/").split("/")[-1]

        req2 = urllib.request.Request(
            ZAPRET_ASSETS_URL.format(tag=tag),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req2, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")

        zips = re.findall(r'href="(/Flowseal/[^"]+\.zip)"', html)
        if zips:
            return tag, "https://github.com" + zips[0]
        return tag, final_url
    except Exception:
        return None, None
def update_zapret(url: str, progress_cb=None, status_cb=None) -> tuple[bool, str]:
    
    tmp_zip = BASE / "_zapret_update.zip"
    tmp_dir = BASE / "_zapret_new"

    def _status(text, detail=""):
        if status_cb:
            status_cb(text, detail)

    try:
        _status("Останавливаю zapret...")
        if zapret_running():
            zapret_stop()
            time.sleep(1)

        _status("Очищаю старую версию...")
        if ZAPRET.exists():
            errors = []
            for item in list(ZAPRET.iterdir()):
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    print(f"[clean] deleted: {item.name}")
                except Exception as e:
                    errors.append(f"{item.name}: {e}")
                    print(f"[clean] FAILED: {item.name}: {e}")
            if errors:
                return False, "Не удалось удалить файлы:\n" + "\n".join(errors)

        _status("Скачиваю архив...", url.split("/")[-1])
        def _reporthook(count, block, total):
            if progress_cb and total > 0:
                progress_cb(int(count * block * 100 / total))

        urllib.request.urlretrieve(url, tmp_zip, _reporthook)

        _status("Распаковываю архив...")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(tmp_dir)

        extracted = list(tmp_dir.iterdir())
        src = extracted[0] if len(extracted) == 1 and extracted[0].is_dir() else tmp_dir

        _status("Устанавливаю файлы...")
        ZAPRET.mkdir(exist_ok=True)
        for name in os.listdir(src):
            item = src / name
            dst  = ZAPRET / name
            print(f"[install] copying: {name}")
            if item.is_file():
                shutil.copy2(item, dst)
            else:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(str(item), str(dst))

        _status("Готово!")
        return True, ""

    except Exception as e:
        return False, str(e)

    finally:
        try:
            tmp_zip.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

def _tg_runner(stop_ev):
    
    global _tg_proc
    entry = TGPROXY / "tgneclocer.exe"
    if not entry.exists():
        return
    try:
        _tg_proc = subprocess.Popen(
            [str(entry)],
            cwd=str(TGPROXY),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        while not stop_ev.is_set():
            if _tg_proc.poll() is not None:
                break
            time.sleep(0.5)
        if _tg_proc and _tg_proc.poll() is None:
            _tg_proc.terminate()
    except Exception:
        pass
    finally:
        _tg_proc = None

def tg_running() -> bool:
    if _tg_proc is not None and _tg_proc.poll() is None:
        return True
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq tgneclocer.exe", "/NH"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stderr=subprocess.DEVNULL,
        ).decode("cp866", errors="ignore")
        return "tgneclocer.exe" in out
    except Exception:
        return False

def tg_start():
    global _tg_thread, _tg_stop
    if tg_running():
        return True, ""
    if not (TGPROXY / "tgneclocer.exe").exists():
        return False, f"Не найден tgneclocer.exe в папке:\n{TGPROXY}"
    _tg_stop   = threading.Event()
    _tg_thread = threading.Thread(target=_tg_runner, args=(_tg_stop,), daemon=True)
    _tg_thread.start()
    time.sleep(1.5)
    return True, ""

def tg_stop():
    _tg_stop.set()
    subprocess.run(
        ["taskkill", "/F", "/IM", "tgneclocer.exe"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True,
    )
    if _tg_proc:
        try:
            _tg_proc.terminate()
        except Exception:
            pass

BG        = "#0d0f14"
CARD      = "#13161e"
BORDER    = "#1e2230"
ACCENT_Z  = "#5865f2"
ACCENT_TG = "#26a5e4"
OFF_COLOR = "#2a2d3a"
TEXT      = "#e8eaf0"
MUTED     = "#555a72"
GREEN     = "#3ba55c"
RED       = "#ed4245"
YELLOW    = "#faa61a"
HOVER     = "#1a1d27"

class ToggleButton(tk.Canvas):
    W, H, R = 52, 28, 14

    def __init__(self, master, accent=ACCENT_Z, command=None, **kw):
        super().__init__(master, width=self.W, height=self.H,
                         bg=CARD, bd=0, highlightthickness=0, **kw)
        self._on = False; self._accent = accent
        self._command = command; self._busy = False
        self._kx = self.R + 2; self._color = OFF_COLOR
        self.bind("<Button-1>", self._click); self._draw()

    def _draw(self):
        self.delete("all"); r = self.R
        for x0, y0, x1, y1 in [(0,0,self.H,self.H),(self.W-self.H,0,self.W,self.H)]:
            self.create_oval(x0,y0,x1,y1,fill=self._color,outline="")
        self.create_rectangle(r,0,self.W-r,self.H,fill=self._color,outline="")
        self.create_oval(self._kx-r+2,2,self._kx+r-2,self.H-2,fill="white",outline="")

    def _click(self, _=None):
        if self._busy: return
        self._busy = True; ns = not self._on
        self._animate((self.W-self.R-2) if ns else (self.R+2),
                      self._accent if ns else OFF_COLOR, ns)

    def _animate(self, tx, tc, ns, step=0, steps=8):
        sx, ex = self.R+2, self.W-self.R-2; p = (step+1)/steps
        self._kx = (sx+(ex-sx)*p) if ns else (ex+(sx-ex)*p)
        self._color = tc; self._draw()
        if step < steps-1:
            self.after(14, lambda: self._animate(tx,tc,ns,step+1,steps))
        else:
            self._kx=tx; self._on=ns; self._draw(); self._busy=False
            if self._command: self._command(ns)

    def set_state(self, state: bool):
        self._on=state; self._kx=(self.W-self.R-2) if state else (self.R+2)
        self._color=self._accent if state else OFF_COLOR; self._draw()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BypassManager")
        self.resizable(False, False)
        self.configure(bg=BG)
        w, h = 440, 560
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._bat_options = get_bat_options()
        self._build()
        self._poll()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(3000, self._check_update_bg)

    def _build(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(22, 2))
        tk.Label(hdr, text="BypassManager", font=("Segoe UI", 22, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(hdr, text=" v1.0", font=("Segoe UI", 10),
                 bg=BG, fg=MUTED).pack(side="left", pady=(10,0))

        self._upd_btn = tk.Button(hdr, text="⟳ Обновить zapret",
                                   font=("Segoe UI", 9), bg=OFF_COLOR, fg=MUTED,
                                   relief="flat", padx=10, pady=4,
                                   cursor="hand2", command=self._on_update_click)
        self._upd_btn.pack(side="right")

        tk.Label(self, text="Управление обходом блокировок",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(anchor="w", padx=24)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=24, pady=14)

        self._z_widgets  = self._make_zapret_card()
        tk.Frame(self, bg=BG, height=10).pack()
        self._tg_widgets = self._make_card(
            "Telegram", "MTProto-прокси tg-ws-proxy", ACCENT_TG, self._toggle_tg)

        tk.Frame(self, bg=BG, height=14).pack()

        self._info_row("🎮  Warframe", " — исключён из обхода", "#43b581")

        tk.Frame(self, bg=BG, height=8).pack()
        self._info_row("🎮  Roblox", " — включён в обход", "#e74c3c")

        tk.Frame(self, bg=BG, height=12).pack()
        tk.Label(self, text="Требуются права администратора",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack()

    def _info_row(self, title, subtitle, color):
        row = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill="x", padx=24)
        tk.Frame(row, bg=color, width=3).pack(side="left", fill="y")
        inner = tk.Frame(row, bg=CARD)
        inner.pack(side="left", padx=12, pady=10)
        tk.Label(inner, text=title, font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=TEXT).pack(side="left")
        tk.Label(inner, text=subtitle, font=("Segoe UI", 9),
                 bg=CARD, fg=MUTED).pack(side="left")

    def _make_zapret_card(self):
        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=24)

        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", padx=16, pady=(14,6))
        left = tk.Frame(top, bg=CARD)
        left.pack(side="left", fill="both", expand=True)
        tk.Frame(left, bg=ACCENT_Z, width=3).pack(side="left", fill="y", padx=(0,12))
        info = tk.Frame(left, bg=CARD); info.pack(side="left")
        tk.Label(info, text="Discord / YouTube",
                 font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(info, text="DPI-обход через zapret",
                 font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(anchor="w")

        right = tk.Frame(top, bg=CARD); right.pack(side="right")
        row = tk.Frame(right, bg=CARD); row.pack(anchor="e", pady=(0,6))
        dot = tk.Label(row, text="●", font=("Segoe UI", 10), bg=CARD, fg=RED)
        dot.pack(side="left")
        lbl = tk.Label(row, text="Выключен", font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        lbl.pack(side="left", padx=(4,0))
        btn = ToggleButton(right, accent=ACCENT_Z, command=self._toggle_z)
        btn.pack(anchor="e")

        bot = tk.Frame(card, bg=CARD); bot.pack(fill="x", padx=16, pady=(0,12))
        tk.Label(bot, text="Вариант:", font=("Segoe UI", 9),
                 bg=CARD, fg=MUTED).pack(side="left")
        saved_label = next(
            (k for k, v in self._bat_options.items() if v == _selected_bat),
            list(self._bat_options.keys())[0]
        )
        var = tk.StringVar(value=saved_label)
        var.trace_add("write", lambda *_: self._on_bat_change(var.get()))
        opt = tk.OptionMenu(bot, var, *list(self._bat_options.keys()))
        opt.config(font=("Segoe UI", 9), bg=CARD, fg=TEXT,
                   activebackground=HOVER, activeforeground=TEXT,
                   highlightthickness=0, relief="flat", bd=0)
        opt["menu"].config(bg=CARD, fg=TEXT, activebackground=ACCENT_Z,
                           activeforeground="white", font=("Segoe UI", 9))
        opt.pack(side="left", padx=(6,0))

        return {"dot": dot, "lbl": lbl, "btn": btn, "accent": ACCENT_Z, "var": var, "opt_menu": opt}

    def _make_card(self, title, subtitle, accent, on_toggle):
        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=24)
        inner = tk.Frame(card, bg=CARD); inner.pack(fill="x", padx=16, pady=16)
        left = tk.Frame(inner, bg=CARD); left.pack(side="left", fill="both", expand=True)
        tk.Frame(left, bg=accent, width=3).pack(side="left", fill="y", padx=(0,12))
        info = tk.Frame(left, bg=CARD); info.pack(side="left")
        tk.Label(info, text=title, font=("Segoe UI", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(info, text=subtitle, font=("Segoe UI", 9),
                 bg=CARD, fg=MUTED).pack(anchor="w")
        right = tk.Frame(inner, bg=CARD); right.pack(side="right")
        row = tk.Frame(right, bg=CARD); row.pack(anchor="e", pady=(0,6))
        dot = tk.Label(row, text="●", font=("Segoe UI", 10), bg=CARD, fg=RED)
        dot.pack(side="left")
        lbl = tk.Label(row, text="Выключен", font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        lbl.pack(side="left", padx=(4,0))
        btn = ToggleButton(right, accent=accent, command=on_toggle)
        btn.pack(anchor="e")
        return {"dot": dot, "lbl": lbl, "btn": btn, "accent": accent}

    def _check_update_bg(self):
        def _work():
            try:
                ver, url = check_zapret_update()
                print(f"[update] ver={ver} url={url}")
                if ver and url:
                    self.after(0, lambda: self._show_update_badge(ver, url))
                else:
                    self.after(0, lambda: self._upd_btn.config(
                        text="✓ Последняя версия", bg=GREEN, fg="white"))
                    self.after(4000, lambda: self._upd_btn.config(
                        text="⟳ Обновить zapret", bg=OFF_COLOR, fg=MUTED))
            except Exception as e:
                print(f"[update] error: {e}")
        threading.Thread(target=_work, daemon=True).start()

    def _show_update_badge(self, ver, url):
        print(f"[badge] showing update badge: {ver}")
        self._pending_url = url
        self._upd_btn.config(
            text=f"⟳ {ver}",
            bg=YELLOW, fg="#0d0f14",
            state="normal",
            command=lambda: self._do_update(url)
        )

    def _on_update_click(self):
        self._upd_btn.config(text="Проверяю...", state="disabled")
        def _work():
            try:
                ver, url = check_zapret_update()
                print(f"[manual update] ver={ver} url={url}")
                def _done():
                    if ver and url:
                        self._show_update_badge(ver, url)
                    else:
                        ver_file = ZAPRET / ".service" / "version.txt"
                        current = ver_file.read_text().strip() if ver_file.exists() else "?"
                        self._upd_btn.config(
                            text=f"✓ {current} — последняя",
                            bg=GREEN, fg="white", state="normal")
                        self.after(4000, lambda: self._upd_btn.config(
                            text="⟳ Обновить zapret", bg=OFF_COLOR, fg=MUTED))
                self.after(0, _done)
            except Exception as e:
                print(f"[manual update] error: {e}")
                self.after(0, lambda: self._upd_btn.config(
                    text="✗ Ошибка", bg=RED, fg="white", state="normal"))
                self.after(4000, lambda: self._upd_btn.config(
                    text="⟳ Обновить zapret", bg=OFF_COLOR, fg=MUTED))
        threading.Thread(target=_work, daemon=True).start()

    def _do_update(self, url):
        win = tk.Toplevel(self)
        win.title("Обновление zapret")
        win.configure(bg=BG); win.resizable(False, False); win.grab_set()
        w, h = 380, 220
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        tk.Label(win, text="Обновление zapret",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=TEXT).pack(pady=(20, 4))

        status_lbl = tk.Label(win, text="Подготовка...",
                              font=("Segoe UI", 10), bg=BG, fg=MUTED)
        status_lbl.pack()

        bar_bg = tk.Frame(win, bg=BORDER, height=6, width=320)
        bar_bg.pack(pady=10)
        bar_bg.pack_propagate(False)
        bar_fill = tk.Frame(bar_bg, bg=ACCENT_Z, height=6)
        bar_fill.place(x=0, y=0, relheight=1, relwidth=0)

        pct_lbl = tk.Label(win, text="", font=("Segoe UI", 9), bg=BG, fg=MUTED)
        pct_lbl.pack()

        detail_lbl = tk.Label(win, text="", font=("Segoe UI", 8),
                              bg=BG, fg=MUTED, wraplength=340)
        detail_lbl.pack(pady=(4, 0))

        def _status(text, detail=""):
            self.after(0, lambda: status_lbl.config(text=text))
            self.after(0, lambda: detail_lbl.config(text=detail))

        def _progress(pct):
            self.after(0, lambda: [
                bar_fill.place(x=0, y=0, relheight=1, relwidth=pct/100),
                pct_lbl.config(text=f"{pct}%"),
                status_lbl.config(text="Скачиваю..."),
            ])

        def _work():
            original_update = update_zapret

            _status("Подготовка...")
            ok, err = update_zapret(url, _progress, _status)
            self._bat_options = get_bat_options()

            def _done():
                win.protocol("WM_DELETE_WINDOW", win.destroy)
                win.destroy()
                if ok:
                    self._upd_btn.config(text="✓ Обновлено", bg=GREEN,
                                         fg="white", state="normal")
                    self.after(4000, lambda: self._upd_btn.config(
                        text="⟳ Обновить zapret", bg=OFF_COLOR, fg=MUTED))
                else:
                    import tkinter.messagebox as mb
                    mb.showerror("Ошибка обновления", err)
                    self._upd_btn.config(text="⟳ Обновить zapret",
                                         bg=OFF_COLOR, fg=MUTED, state="normal")
            self.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def _on_bat_change(self, name):
        global _selected_bat
        _selected_bat = self._bat_options.get(name, "general.bat")
        _save_prefs()

    def _toggle_z(self, state):
        if state:
            ok, err = zapret_start()
            if not ok:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка запуска zapret", err)
                self._z_widgets["btn"].set_state(False)
                self._update_card(self._z_widgets, False)
        else:
            zapret_stop()
            self._update_card(self._z_widgets, False)

    def _toggle_tg(self, state):
        if state:
            ok, err = tg_start()
            if not ok:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка запуска Telegram", err)
                self._tg_widgets["btn"].set_state(False)
                self._update_card(self._tg_widgets, False)
        else:
            tg_stop()
            self._update_card(self._tg_widgets, False)

    def _update_card(self, w, running):
        if running:
            w["dot"].config(fg=GREEN); w["lbl"].config(text="Работает", fg=GREEN)
        else:
            w["dot"].config(fg=RED); w["lbl"].config(text="Выключен", fg=MUTED)
        w["btn"].set_state(running)

    def _poll(self):
        self._update_card(self._z_widgets,  zapret_running())
        self._update_card(self._tg_widgets, tg_running())
        self.after(2000, self._poll)

    def _on_close(self):
        zapret_stop(); tg_stop(); self.destroy()

def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _relaunch_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable,
        " ".join(f'"{a}"' for a in sys.argv), None, 1)

if __name__ == "__main__":
    if not _is_admin():
        _relaunch_as_admin()
        sys.exit(0)
    try:
        App().mainloop()
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror("Критическая ошибка", str(e))
