import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


PROMPT_TEMPLATE = """Lee @{path} ({w}x{h} px) con Read. Es una pregunta de opcion multiple (A/B/C/D, 1/2/3/4, tiles Kahoot, cards, botones, radios). Las opciones pueden ser texto, numeros, formulas o imagenes.

Resuelve la pregunta y devolve el centro visual de la opcion correcta en coordenadas de la imagen (origen top-left). Si son tiles grandes apunta al centro del tile, no al badge chico. correct_letter = "A","B","C","D" o "1","2","3","4" segun lo que muestre la pantalla. Solo found=false si de verdad no ves una pregunta.

Responde UNA sola linea de JSON, sin markdown:
{{"found":true,"correct_letter":"B","correct_text":"...","x":123,"y":456,"confidence":0.0}}
"""


CREATE_NO_WINDOW = 0x08000000
MAX_WIDTH = int(os.environ.get("RESPUESTASINADOR_MAX_WIDTH", "1280"))
JPEG_QUALITY = int(os.environ.get("RESPUESTASINADOR_JPEG_QUALITY", "82"))

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS


def _stripFences(text):
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return m.group(1).strip() if m else text


class _BaseBrain:
    name = "base"

    def __init__(self):
        self.cli = self._findCli()
        self.model = os.environ.get("RESPUESTASINADOR_MODEL") or None
        self.timeout = int(os.environ.get("RESPUESTASINADOR_TIMEOUT", "120"))

    def _findCli(self):
        raise NotImplementedError

    def _buildArgs(self, prompt):
        raise NotImplementedError

    def _extractText(self, outer):
        raise NotImplementedError

    def analyze(self, image):
        origW, origH = image.size
        if origW > MAX_WIDTH:
            scale = MAX_WIDTH / origW
            scaled = image.resize((MAX_WIDTH, int(round(origH * scale))), resample=_RESAMPLE)
        else:
            scale = 1.0
            scaled = image

        fd, tmpName = tempfile.mkstemp(prefix="rs_", suffix=".jpg")
        os.close(fd)
        imgPath = Path(tmpName)
        scaled.save(str(imgPath), format="JPEG", quality=JPEG_QUALITY, optimize=False, progressive=False)

        try:
            prompt = PROMPT_TEMPLATE.format(
                path=imgPath.as_posix(), w=scaled.size[0], h=scaled.size[1]
            )
            args = self._buildArgs(prompt)
            try:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
            except subprocess.TimeoutExpired:
                return {"found": False, "error": f"timeout tras {self.timeout}s"}

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                return {"found": False, "error": stderr[:400] or f"exit {result.returncode}"}

            raw = result.stdout.strip()
            inner = raw
            try:
                outer = json.loads(raw)
                if isinstance(outer, dict):
                    extracted = self._extractText(outer)
                    if extracted is not None:
                        inner = str(extracted)
            except json.JSONDecodeError:
                pass

            inner = _stripFences(inner.strip())
            try:
                parsed = json.loads(inner)
            except json.JSONDecodeError:
                return {"found": False, "raw": inner[:400]}

            if scale != 1.0 and parsed.get("found"):
                for k in ("x", "y"):
                    v = parsed.get(k)
                    if isinstance(v, (int, float)):
                        parsed[k] = int(round(v / scale))

            return parsed
        finally:
            try:
                imgPath.unlink()
            except OSError:
                pass


class ClaudeBrain(_BaseBrain):
    name = "claude"

    def _findCli(self):
        p = shutil.which("claude")
        if p:
            return p
        for cand in [
            Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "claude.exe",
            Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "claude.cmd",
            Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "claude" / "claude.exe",
        ]:
            if cand.exists():
                return str(cand)
        raise RuntimeError("No encuentro 'claude' CLI en PATH ni en rutas tipicas")

    def _buildArgs(self, prompt):
        args = [
            self.cli, "-p", prompt,
            "--output-format", "json",
            "--allowed-tools", "Read",
            "--permission-mode", "acceptEdits",
        ]
        if self.model:
            args += ["--model", self.model]
        return args

    def _extractText(self, outer):
        if outer.get("is_error"):
            return outer.get("result")
        return outer.get("result")


class AntigravityBrain(_BaseBrain):
    name = "antigravity"

    def _findCli(self):
        p = shutil.which("agy")
        if p:
            return p
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if winget.exists():
            try:
                for d in winget.iterdir():
                    if "AntigravityCLI" in d.name:
                        exe = d / "agy.exe"
                        if exe.exists():
                            return str(exe)
            except OSError:
                pass
        for cand in [
            Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "agy.exe",
            Path(os.environ.get("APPDATA", "")) / "npm" / "agy.cmd",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity" / "agy.exe",
        ]:
            if cand.exists():
                return str(cand)
        raise RuntimeError("No encuentro 'agy' (Antigravity CLI) en PATH ni WinGet")

    def _buildArgs(self, prompt):
        args = [
            self.cli, "-p", prompt,
            "--output-format", "json",
            "--mode", "accept-edits",
        ]
        if self.model:
            args += ["--model", self.model]
        return args

    def _extractText(self, outer):
        status = outer.get("status")
        if status and status != "SUCCESS":
            return outer.get("response") or outer.get("error") or f"status={status}"
        return outer.get("response")


_BACKENDS = {
    "claude": ClaudeBrain,
    "cc": ClaudeBrain,
    "claude-code": ClaudeBrain,
    "antigravity": AntigravityBrain,
    "agy": AntigravityBrain,
    "ag": AntigravityBrain,
    "google": AntigravityBrain,
}


def Brain():
    backend = (os.environ.get("RESPUESTASINADOR_BACKEND") or "claude").lower().strip()
    cls = _BACKENDS.get(backend)
    if cls is None:
        raise RuntimeError(f"Backend desconocido: '{backend}' (opciones: claude, antigravity)")
    return cls()
