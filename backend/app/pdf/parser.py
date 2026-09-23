"""PDF text extraction (pypdf). Files are UNTRUSTED DATA."""
from io import BytesIO
import re

# Raw-byte markers for embedded active content. The lab NEVER executes
# these — it only detects and flags them, like an AV scanner flags EICAR.
_SCRIPT_MARKERS = [b"/JS", b"/JavaScript", b"/AA", b"/OpenAction",
                   b"/EmbeddedFile", b"/XFA", b"/Launch"]


def extract_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        text = "\n".join([(p.extract_text() or "") for p in reader.pages])
        if text.strip():
            return text[:20000]
    except Exception:
        pass
    # Fallback: treat raw bytes as text (lets tests seed poison without a real PDF)
    try:
        return data.decode("utf-8", errors="ignore")[:20000]
    except Exception:
        return ""


def chunk(text: str, size: int = 500) -> list:
    text = (text or "").strip()
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


# Spans set smaller than this are treated as hidden micro-text (the classic
# white-on-white / footer-noise smuggling trick). Our artifacts use 6-7.5pt
# for payloads vs 11-16pt for body copy.
HIDDEN_FONT_SIZE = 8.0


def extract_layers(data: bytes) -> dict:
    """Split a PDF into VISIBLE body text vs HIDDEN micro-text.

    The LLM is only ever given the visible layer; the hidden layer is kept
    server-side and (in vulnerable mode) pasted after the answer by the
    backend itself. Returns {visible, hidden}.
    """
    visible: list = []
    hidden: list = []
    try:
        from pypdf import PdfReader

        def visitor(text, cm, tm, font_dict, font_size):
            if not text or not text.strip():
                return
            try:
                size = float(font_size)
            except (TypeError, ValueError):
                size = 12.0
            (hidden if size < HIDDEN_FONT_SIZE else visible).append(text)

        reader = PdfReader(BytesIO(data))
        try:
            for page in reader.pages:
                page.extract_text(visitor_text=visitor)
        except TypeError:
            # ancient pypdf without visitor support: plain extract = visible
            plain = "\n".join([(p.extract_text() or "") for p in reader.pages])
            return {"visible": plain[:20000], "hidden": ""}
        if visible or hidden:
            return {"visible": "\n".join(visible)[:20000],
                    "hidden": "\n".join(hidden)[:20000]}
    except Exception:
        pass
    # Fallback (raw bytes / unparsable): everything counts as visible.
    try:
        return {"visible": data.decode("utf-8", errors="ignore")[:20000],
                "hidden": ""}
    except Exception:
        return {"visible": "", "hidden": ""}


def detect_scripting(data: bytes) -> dict:
    """Scan raw PDF bytes for embedded-script markers. Detection only —
    the lab never executes embedded code."""
    found = sorted({m.decode() for m in _SCRIPT_MARKERS if m in (data or b"")})
    return {"scripting_detected": bool(found), "markers": found}
