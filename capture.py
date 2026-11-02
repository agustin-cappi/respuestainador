import mss
from PIL import Image


def grabPrimary():
    with mss.mss() as sct:
        mon = sct.monitors[1]
        raw = sct.grab(mon)
        img = Image.frombytes("RGB", raw.size, raw.rgb)
        return img, (mon["left"], mon["top"], mon["width"], mon["height"])
