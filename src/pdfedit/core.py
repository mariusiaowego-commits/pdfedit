"""
Core PDF text replacement — preserves font, size, color, position.

Strategy:
  1. Extract embedded font buffers from the PDF (FontFile2 / FontFile3 streams)
  2. Register each font under a stable custom name via insert_font(fontbuffer=...)
     — registration is page-scoped in PyMuPDF, so cache per (xref, page_idx)
  3. Redact the old text span (white fill = erase glyphs, preserve background)
  4. Insert new text at the same position with the extracted font
  5. Save with incremental update to avoid corrupting the original
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import fitz


# -------------------------------------------------------------------
# Font cache — extract each unique font buffer once per (xref, page)
# -------------------------------------------------------------------

class FontCache:
    """Extracts and caches embedded font buffers from a PDF.

    PyMuPDF's insert_font() is page-scoped — a font registered on one page
    cannot be used on another. We therefore cache per (xref, page_idx).
    """

    def __init__(self, doc: fitz.Document, fallback_fontfile: str | None = None):
        self.doc = doc
        # page_idx → {xref → font_bytes}
        self._buf_cache: dict[int, dict[int, bytes]] = {}
        # (xref, page_idx) → registered font name on that page
        self._name_map: dict[tuple[int, int], str] = {}
        # Fallback font file path (used when primary font is missing glyphs)
        self._fallback_fontfile = fallback_fontfile or self._find_chinese_fallback()
        self._fallback_name: str | None = None
        # Track which pages have been preloaded (to avoid re-preloading after redaction)
        self._preloaded_pages: set[int] = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_xref(ref_str: str) -> int | None:
        """Extract integer xref from a string like '234 0 R' or '[235 0 R]'."""
        if not ref_str or ref_str == "null":
            return None
        m = re.search(r"(\d+)", ref_str)
        return int(m.group(1)) if m else None

    def _get_font_file_stream(self, fd_xref: int) -> Optional[bytes]:
        """Extract raw bytes from a FontDescriptor's FontFile2/3 stream."""
        for key in ["FontFile2", "FontFile3", "FontFile"]:
            ref = self.doc.xref_get_key(fd_xref, key)[1]
            if not ref or ref == "null":
                continue
            stream_xref = self._parse_xref(ref)
            if stream_xref:
                stream = self.doc.xref_stream(stream_xref)
                if stream:
                    return stream
        return None

    def _extract_font_buffer(self, xref: int, page_idx: int) -> Optional[bytes]:
        """Walk the PDF font object tree to find the raw TTF/OTF bytes.

        Font buffers are cached per page since apply_redactions() can
        invalidate xref streams after the document is modified.
        """
        if page_idx in self._buf_cache and xref in self._buf_cache[page_idx]:
            return self._buf_cache[page_idx][xref]

        stream = None

        # Case 1: Type0 font → DescendantFonts[0] → FontDescriptor → FontFile2
        subtype = self.doc.xref_get_key(xref, "Subtype")[1]
        if subtype == "/Type0":
            desc_ref = self.doc.xref_get_key(xref, "DescendantFonts")[1]
            desc_xref = self._parse_xref(desc_ref)
            if desc_xref:
                fd_ref = self.doc.xref_get_key(desc_xref, "FontDescriptor")[1]
                fd_xref = self._parse_xref(fd_ref)
                if fd_xref:
                    stream = self._get_font_file_stream(fd_xref)

        # Case 2: Direct FontDescriptor on the font object itself
        if not stream:
            fd_ref = self.doc.xref_get_key(xref, "FontDescriptor")[1]
            fd_xref = self._parse_xref(fd_ref)
            if fd_xref:
                stream = self._get_font_file_stream(fd_xref)

        if stream:
            self._buf_cache.setdefault(page_idx, {})[xref] = stream
        return stream

    def preload_page(self, page: fitz.Page) -> None:
        """Pre-extract and cache all font buffers for one page.

        Call this BEFORE any apply_redactions() on the document.
        This guards against apply_redactions() invalidating xref streams.
        """
        for xref, _, subtype, base_font, *_ in page.get_fonts():
            self._extract_font_buffer(xref, page.number)

    @staticmethod
    def _find_chinese_fallback() -> str | None:
        """Find a system Chinese font to use as fallback for missing glyphs."""
        candidates = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]
        for path in candidates:
            import os
            if os.path.exists(path):
                return path
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_fallback_name(self, page: fitz.Page) -> str:
        """Register the fallback font on this page and return the registered name.

        IMPORTANT: always registers with a fresh unique name because PyMuPDF
        invalidates name→buffer mappings after apply_redactions().
        Does NOT check get_fonts() first — that call itself can mutate PyMuPDF state.
        """
        if self._fallback_fontfile is None:
            raise RuntimeError("No fallback font available for missing glyphs")
        with open(self._fallback_fontfile, "rb") as f:
            fb = f.read()
        import uuid
        name = f"pdfedit_fb_{uuid.uuid4().hex[:8]}"
        page.insert_font(fontname=name, fontbuffer=fb)
        return name

    def get_registered_name(
        self, original_fontname: str, original_xref: int, page: fitz.Page
    ) -> str:
        """Register the font on `page` and return a fresh registered name.

        Uses doc.extract_font() on every call — no caching of the font name,
        because PyMuPDF's internal font cache is invalidated by apply_redactions().
        """
        # extract_font() is reliable even after redactions (unlike xref_stream)
        name, ext, _, font_bytes = self.doc.extract_font(original_xref)
        if not font_bytes:
            raise RuntimeError(
                f"Cannot extract font buffer for '{original_fontname}' (xref={original_xref}). "
                "This PDF may use a font format not supported for text replacement."
            )

        # Always use a fresh unique name — PyMuPDF invalidates the name→buffer
        # mapping after apply_redactions() even if the buffer bytes are the same
        import uuid
        custom_name = f"pdfedit_{original_xref}_{uuid.uuid4().hex[:8]}"
        page.insert_font(fontname=custom_name, fontbuffer=font_bytes)
        return custom_name


# -------------------------------------------------------------------
# Core API
# -------------------------------------------------------------------

def load_pdf(path: str | Path) -> fitz.Document:
    return fitz.open(str(path))


def save_pdf(doc: fitz.Document, path: str | Path) -> None:
    doc.save(str(path), incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)


def find_spans(
    doc: fitz.Document,
    text: str,
    page_idx: int | None = None,
    font: str | None = None,
    size: float | None = None,
    size_tolerance: float = 1.0,
) -> list[tuple[int, dict]]:
    """
    Find all text spans matching `text` exactly.

    Args:
        doc: opened PyMuPDF document
        text: exact text to find
        page_idx: limit search to one page (None = all pages)
        font: match font name exactly
        size: match font size within size_tolerance
        size_tolerance: tolerance for size comparison (default 1.0 pt)

    Returns:
        [(page_idx, span_dict), ...]
    """
    results = []
    pages = [doc[page_idx]] if page_idx is not None else doc
    for page in pages:
        raw = page.get_text("dict")
        for block in raw["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"] != text:
                        continue
                    if font and span["font"] != font:
                        continue
                    if size is not None and abs(span["size"] - size) > size_tolerance:
                        continue
                    results.append((page.number, span))
    return results


def _unpack_color(color_val) -> tuple[float, float, float]:
    """Convert PyMuPDF color (int 0-0xFFFFFF or 3-tuple) to (r,g,b) 0-1."""
    if isinstance(color_val, (int, float)):
        i = int(color_val)
        return ((i >> 16) & 0xFF) / 255.0, ((i >> 8) & 0xFF) / 255.0, (i & 0xFF) / 255.0
    return tuple(color_val)  # type: ignore[return-value]


def _needs_fallback(text: str, original_fontname: str, registered_fontname: str) -> bool:
    """Return True if any character in `text` might be missing from the font.

    Detects glyphs that would render as tofu (empty) by checking if the
    original font is a 方正黑体 subset (B01S) — these subsets are often
    incomplete for less-common characters like '号'.
    """
    combined = original_fontname + registered_fontname
    if "B01S" in combined or "FangZheng" in combined.upper() or "fangzheng" in combined.lower():
        # Check for characters that commonly fail in 方正 subsets
        problematic = {"号", "龍", "龟", "鳳", "麤", "灥"}
        return any(ch in problematic for ch in text)
    return False


def _split_runs(text: str) -> list[tuple[str, str | None]]:
    """Split text into runs of same-script characters.

    Returns list of (run_text, font_name_or_none) where font_name_or_none
    is None for Latin/ASCII characters (will use base14 Helvetica).
    """
    runs = []
    current = ""
    is_cjk = None
    for ch in text:
        cjk = ord(ch) > 0x3000  # CJK Unified Ideographs + punctuation
        if is_cjk is None:
            is_cjk = cjk
            current = ch
        elif cjk != is_cjk:
            runs.append((current, None if not is_cjk else "cjk"))
            current = ch
            is_cjk = cjk
        else:
            current += ch
    runs.append((current, None if not is_cjk else "cjk"))
    return runs


def replace_span(
    doc: fitz.Document,
    page_idx: int,
    span: dict,
    new_text: str,
    font_cache: FontCache | None = None,
    fill_color: tuple[float, float, float] | None = None,
) -> None:
    """
    Replace one text span in-place, preserving visual appearance.

    Steps:
      1. Redact the old span area (white fill = erase glyphs, keep page background)
      2. Register the original font + fallback on this specific page
      3. Insert new text, using fallback font for chars missing from original

    Args:
        doc: opened PyMuPDF document
        page_idx: 0-based page number
        span: span dict from get_text("dict")
        new_text: replacement string
        font_cache: pre-initialized FontCache; created if None
        fill_color: (r,g,b) 0-1 for the new text; None = original color
    """
    page = doc[page_idx]
    orig_rect = fitz.Rect(span["bbox"])

    # Step 1: redact old glyphs with white fill
    page.add_redact_annot(orig_rect, fill=(1, 1, 1))
    page.apply_redactions()

    # Step 2: find original font xref on this page
    font_xref = None
    for xref, _, subtype, base_font, *_ in page.get_fonts():
        if base_font == span["font"]:
            font_xref = xref
            break

    if font_xref is None:
        raise RuntimeError(f"Font '{span['font']}' not found in PDF fonts.")

    # Register original font (fresh name each time via extract_font + unique name)
    registered_name = font_cache.get_registered_name(span["font"], font_xref, page)
    fontsize = span["size"]
    color = fill_color if fill_color is not None else _unpack_color(span.get("color", 0))
    insert_pos = fitz.Point(orig_rect.x0, orig_rect.y1)

    # Step 3: decide which font to use for new text
    use_fallback = _needs_fallback(new_text, span["font"], registered_name)
    actual_font = font_cache.get_fallback_name(page) if use_fallback else registered_name

    if use_fallback:
        print(f"  [fallback] using STHeiti for '{new_text}' (missing glyphs in '{span['font']}')")

    page.insert_text(insert_pos, new_text, fontname=actual_font,
                     fontsize=fontsize, color=color)


def replace_all(
    doc: fitz.Document,
    old_text: str,
    new_text: str,
    page_idx: int | None = None,
    font: str | None = None,
    size: float | None = None,
    size_tolerance: float = 1.0,
) -> int:
    """
    Find all spans matching old_text exactly and replace with new_text.

    Returns:
        Number of spans replaced.
    """
    font_cache = FontCache(doc)
    spans = find_spans(doc, old_text, page_idx=page_idx,
                       font=font, size=size, size_tolerance=size_tolerance)
    for p_idx, span in spans:
        replace_span(doc, p_idx, span, new_text, font_cache=font_cache)
    return len(spans)
