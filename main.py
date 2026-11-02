import os
import sys
import time
import threading
import traceback
import functools
import ctypes
from datetime import datetime
from pathlib import Path

print = functools.partial(print, flush=True)


def _setDpiAware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return "per-monitor-v2"
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return "system"
    except (AttributeError, OSError):
        return "none"

from dotenv import load_dotenv
import keyboard

from capture import grabPrimary
from brain import Brain
from overlay import Overlay


def _appDir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _loadEnv():
    envPath = _appDir() / ".env"
    if envPath.exists():
        load_dotenv(envPath)
    else:
        load_dotenv()


def _redirectIoIfNeeded():
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        logPath = _appDir() / "respuestasinador.log"
        f = open(logPath, "a", encoding="utf-8", buffering=1)
    except OSError:
        import io
        f = io.StringIO()
    if sys.stdout is None:
        sys.stdout = f
    if sys.stderr is None:
        sys.stderr = f


_MB_OK = 0x0
_MB_ICONERROR = 0x10
_MB_ICONWARNING = 0x30
_MB_SYSTEMMODAL = 0x1000


def _popup(title, message, icon=_MB_ICONERROR):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, _MB_OK | icon | _MB_SYSTEMMODAL)
    except Exception as e:
        print(f"[popup fail] {e}")


def _buildBrainOrPopup():
    backend = (os.environ.get("RESPUESTASINADOR_BACKEND") or "claude").lower().strip()
    try:
        return Brain()
    except RuntimeError as e:
        print(f"[fatal] {e}")
        if backend in ("antigravity", "agy", "ag", "google"):
            msg = (
                f"{e}\n\n"
                "Como instalarlo:\n"
                "  1) Abri PowerShell y corre:\n"
                "         winget install Google.AntigravityCLI\n"
                "     (o descargalo desde https://antigravity.google)\n"
                "  2) Corre 'agy' en una terminal para loguearte\n"
                "     con tu cuenta de Google.\n\n"
                "Despues corre verificar.bat para comprobar que este todo bien."
            )
        else:
            msg = (
                f"{e}\n\n"
                "Como instalarlo:\n"
                "  1) Instala Node.js desde https://nodejs.org\n"
                "  2) Abri una terminal y corre:\n"
                "         npm install -g @anthropic-ai/claude-code\n"
                "  3) Corre 'claude' en una terminal para loguearte.\n\n"
                "Despues corre verificar.bat para comprobar que este todo bien."
            )
        _popup("Respuestasinador - falta instalar el CLI", msg)
        sys.exit(1)


HOTKEY_SCAN = os.environ.get("RESPUESTASINADOR_HOTKEY_SCAN", "f8")
HOTKEY_CLEAR = os.environ.get("RESPUESTASINADOR_HOTKEY_CLEAR", "")
HOTKEY_QUIT = os.environ.get("RESPUESTASINADOR_HOTKEY_QUIT", "f9")


class App:
    def __init__(self):
        self.brain = _buildBrainOrPopup()
        self.overlay = Overlay()
        self.running = True
        self.busy = False
        self._pending = None
        self._clearRequested = False

    def _scanWorker(self):
        try:
            t0 = time.perf_counter()
            self._clearRequested = True
            for _ in range(20):
                if not self._clearRequested:
                    break
                time.sleep(0.005)
            tClear = time.perf_counter()
            img, mon = grabPrimary()
            tCap = time.perf_counter()
            print(f"[scan] capturado {img.size[0]}x{img.size[1]} (monitor {mon[2]}x{mon[3]})")
            result = self.brain.analyze(img)
            tLLM = time.perf_counter()
            self._dumpDebug(img, result)
            print(f"[time] clear={tClear-t0:.2f}s cap={tCap-tClear:.2f}s llm={tLLM-tCap:.2f}s total={tLLM-t0:.2f}s")
            if result.get("found"):
                letter = result.get("correct_letter") or "?"
                text = (result.get("correct_text") or "").strip()
                conf = result.get("confidence")
                suffix = f" ({conf:.2f})" if isinstance(conf, (int, float)) else ""
                print(f"[hit] {letter}{suffix} @ ({result['x']},{result['y']}) -> {text[:120]}")
                self._pending = (int(result["x"]), int(result["y"]), letter)
            else:
                err = result.get("error") or result.get("raw") or "sin pregunta visible"
                print(f"[miss] {err[:200]}")
        except Exception as e:
            print(f"[error] {e}")
            traceback.print_exc()
        finally:
            self.busy = False

    def _dumpDebug(self, img, result):
        try:
            dbg = _appDir() / "debug"
            dbg.mkdir(exist_ok=True)
            existing = sorted(dbg.glob("scan_*.png"))
            for old in existing[:-4]:
                try:
                    old.unlink()
                    old.with_suffix(".json").unlink(missing_ok=True)
                except OSError:
                    pass
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img.save(dbg / f"scan_{stamp}.png")
            import json as _json
            (dbg / f"scan_{stamp}.json").write_text(
                _json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            print(f"[debug] no se pudo volcar: {e}")

    def onScan(self):
        if self.busy:
            return
        self.busy = True
        print("[scan] analizando...")
        threading.Thread(target=self._scanWorker, daemon=True).start()

    def onClear(self):
        self._clearRequested = True

    def onQuit(self):
        self.running = False

    def run(self):
        keyboard.add_hotkey(HOTKEY_SCAN, self.onScan)
        if HOTKEY_CLEAR:
            keyboard.add_hotkey(HOTKEY_CLEAR, self.onClear)
        keyboard.add_hotkey(HOTKEY_QUIT, self.onQuit)

        model = self.brain.model or "(default del backend)"
        print(f"[ready] backend={self.brain.name}")
        print(f"        cli={self.brain.cli}")
        print(f"        modelo={model}")
        print(f"        {HOTKEY_SCAN.upper()} = escanear")
        if HOTKEY_CLEAR:
            print(f"        {HOTKEY_CLEAR.upper()} = quitar overlay")
        print(f"        {HOTKEY_QUIT.upper()} = salir")

        while self.running:
            if self._clearRequested:
                self.overlay.clear()
                self._clearRequested = False
            if self._pending is not None:
                x, y, label = self._pending
                self._pending = None
                self.overlay.showMark(x, y, label)
            self.overlay.pump()
            time.sleep(0.016)

        self.overlay.clear()
        print("[bye]")


def main():
    _redirectIoIfNeeded()
    _loadEnv()
    dpi = _setDpiAware()
    print(f"[boot] dpi={dpi}")
    try:
        App().run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[fatal] {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
