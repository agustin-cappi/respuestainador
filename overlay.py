import os
import tkinter as tk
import ctypes


GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000


def _envInt(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Overlay:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.size = _envInt("RESPUESTASINADOR_X_SIZE", 7)
        self.thick = _envInt("RESPUESTASINADOR_X_THICK", 2)
        self.color = os.environ.get("RESPUESTASINADOR_X_COLOR", "#000000")
        self.showLabel = os.environ.get("RESPUESTASINADOR_X_LABEL", "0") == "1"

    def _applyClickThrough(self):
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        user32 = ctypes.windll.user32
        exStyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        exStyle |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exStyle)

    def _ensureWindow(self):
        if self.root is not None:
            return
        chroma = "#ff00ff"
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", chroma)
        self.root.configure(bg=chroma)
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+0+0")
        self.canvas = tk.Canvas(
            self.root, bg=chroma, highlightthickness=0, width=w, height=h, cursor="arrow"
        )
        self.canvas.pack()
        self.root.update_idletasks()
        self._applyClickThrough()

    def showMark(self, x, y, label=""):
        self._ensureWindow()
        self.canvas.delete("all")

        s = self.size
        self.canvas.create_line(x - s, y - s, x + s, y + s, fill=self.color, width=self.thick)
        self.canvas.create_line(x - s, y + s, x + s, y - s, fill=self.color, width=self.thick)

        if label and self.showLabel:
            self.canvas.create_text(
                x + s + 4, y, text=label, fill=self.color,
                font=("Segoe UI", 9), anchor="w",
            )

        self.root.update_idletasks()

    def clear(self):
        if self.root is None:
            return
        try:
            self.root.destroy()
        finally:
            self.root = None
            self.canvas = None

    def pump(self):
        if self.root is None:
            return
        try:
            self.root.update()
        except tk.TclError:
            self.root = None
            self.canvas = None
