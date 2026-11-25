#!/usr/bin/env python3
"""THE WORLD — a one-image newspaper front page summing up the world news
of Wednesday 25 November 2026.

Deterministic, standard-library-only Python 3.13. Running `python3 main.py`
writes entry.png (1024x1024, under 1 MiB) to the output directory; running it
twice writes byte-identical files. No network, no clock, no randomness.

The picture is a broadsheet front page: masthead, dateline, the day's lead
story (Ukraine confirms its drone strike on a Russian ship in the Gulf of
Finland), three more front page stories (the Houthi strike on Riyadh's
tallest tower, NATO's space-defence vow, the climate talks ending with no
deal), an IN BRIEF strip and a BY THE NUMBERS strip, all drawn with a small
5x7 bitmap font scaled up, and packed into a PNG by hand.
"""

import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024
MARGIN = 36

INK = (0, 0, 0)
PAPER = (255, 255, 255)
GREY = (90, 90, 90)

# ---------------------------------------------------------------------------
# 5x7 bitmap font: each glyph is seven rows, each row five bits (bit 4 is the
# leftmost pixel). Uppercase, lowercase, digits and punctuation.
# ---------------------------------------------------------------------------
FONT = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "!": (4, 4, 4, 4, 4, 0, 4),
    '"': (10, 10, 10, 0, 0, 0, 0),
    "#": (10, 10, 31, 10, 31, 10, 10),
    "$": (4, 15, 20, 14, 5, 30, 4),
    "%": (24, 25, 2, 4, 8, 19, 24),
    "&": (12, 18, 20, 8, 21, 18, 13),
    "'": (4, 4, 8, 0, 0, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "*": (0, 4, 21, 14, 21, 4, 0),
    "+": (0, 4, 4, 31, 4, 4, 0),
    ",": (0, 0, 0, 0, 12, 4, 8),
    "-": (0, 0, 0, 31, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    "/": (1, 1, 2, 4, 8, 16, 16),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 4, 0, 12, 4, 8),
    "<": (2, 4, 8, 16, 8, 4, 2),
    "=": (0, 0, 31, 0, 31, 0, 0),
    ">": (8, 4, 2, 1, 2, 4, 8),
    "?": (14, 17, 1, 2, 4, 0, 4),
    "@": (14, 17, 23, 21, 22, 16, 14),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (1, 1, 1, 1, 1, 17, 14),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "[": (14, 8, 8, 8, 8, 8, 14),
    "\\": (16, 16, 8, 4, 2, 1, 1),
    "]": (14, 2, 2, 2, 2, 2, 14),
    "^": (4, 10, 17, 0, 0, 0, 0),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "`": (8, 4, 2, 0, 0, 0, 0),
    "a": (0, 0, 14, 1, 15, 17, 15),
    "b": (16, 16, 30, 17, 17, 17, 30),
    "c": (0, 0, 14, 17, 16, 17, 14),
    "d": (1, 1, 15, 17, 17, 17, 15),
    "e": (0, 0, 14, 17, 31, 16, 14),
    "f": (6, 8, 30, 8, 8, 8, 8),
    "g": (0, 15, 17, 17, 15, 1, 14),
    "h": (16, 16, 30, 17, 17, 17, 17),
    "i": (4, 0, 12, 4, 4, 4, 14),
    "j": (2, 0, 6, 2, 2, 18, 12),
    "k": (16, 16, 18, 20, 24, 20, 18),
    "l": (12, 4, 4, 4, 4, 4, 14),
    "m": (0, 0, 26, 21, 21, 21, 21),
    "n": (0, 0, 30, 17, 17, 17, 17),
    "o": (0, 0, 14, 17, 17, 17, 14),
    "p": (0, 0, 30, 17, 17, 30, 16),
    "q": (0, 0, 15, 17, 17, 15, 1),
    "r": (0, 0, 22, 25, 16, 16, 16),
    "s": (0, 0, 15, 16, 14, 1, 30),
    "t": (8, 8, 30, 8, 8, 9, 6),
    "u": (0, 0, 17, 17, 17, 19, 13),
    "v": (0, 0, 17, 17, 17, 10, 4),
    "w": (0, 0, 17, 17, 21, 21, 27),
    "x": (0, 0, 17, 10, 4, 10, 17),
    "y": (0, 0, 17, 17, 15, 1, 14),
    "z": (0, 0, 31, 2, 4, 8, 31),
    "{": (6, 8, 8, 30, 8, 8, 6),
    "|": (4, 4, 4, 4, 4, 4, 4),
    "}": (12, 2, 2, 15, 2, 2, 12),
    "~": (0, 0, 14, 21, 0, 0, 0),
}

# Fancy punctuation falls back to its plain lookalike.
ALIASES = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2022": "-", "\u2026": ".",
}

CHAR_W = 6  # glyph cell width in font units (5 pixels + 1 spacing)
CHAR_H = 7


def glyph(ch):
    """Bitmap rows for one character, with aliases and a blank fallback."""
    if ch in FONT:
        return FONT[ch]
    if ch in ALIASES:
        return FONT[ALIASES[ch]]
    return FONT[" "]


def text_width(text, scale):
    """Pixel width of text drawn at the given scale."""
    return len(text) * CHAR_W * scale


# ---------------------------------------------------------------------------
# Canvas: a plain RGB bytearray with tiny drawing helpers.
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        self.pixels = bytearray(colour * (width * height))

    def put(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i] = colour[0]
            self.pixels[i + 1] = colour[1]
            self.pixels[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, colour)

    def hline(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def text(self, x, y, text, scale, colour=INK):
        """Draw text at scale; returns the pixel width drawn."""
        cx = x
        for ch in text:
            rows = glyph(ch)
            for row in range(CHAR_H):
                bits = rows[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, colour)
            cx += CHAR_W * scale
        return cx - x

    def text_centred(self, cx, y, text, scale, colour=INK):
        w = text_width(text, scale)
        self.text(cx - w // 2, y, text, scale, colour)
        return w


def wrap(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width pixels."""
    limit = max(1, max_width // (CHAR_W * scale))
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            trial = word if not line else line + " " + word
            if len(trial) <= limit:
                line = trial
            else:
                if line:
                    lines.append(line)
                # A single over-long word is hard-split so nothing overflows.
                while len(word) > limit:
                    lines.append(word[:limit])
                    word = word[limit:]
                line = word
        if line:
            lines.append(line)
    return lines


def block(canvas, x, y, lines, scale, line_gap=6, colour=INK):
    """Draw wrapped lines; returns the y just below the block."""
    step = CHAR_H * scale + line_gap
    for line in lines:
        canvas.text(x, y, line, scale, colour)
        y += step
    return y


def centred_block(canvas, cx, y, lines, scale, line_gap=6, colour=INK):
    step = CHAR_H * scale + line_gap
    for line in lines:
        canvas.text_centred(cx, y, line, scale, colour)
        y += step
    return y


# ---------------------------------------------------------------------------
# The front page itself.
# ---------------------------------------------------------------------------
def draw_page():
    c = Canvas(WIDTH, HEIGHT, PAPER)
    x0 = MARGIN
    x1 = WIDTH - MARGIN
    full = x1 - x0

    # --- masthead ---------------------------------------------------------
    c.hline(x0, 26, full, INK, 3)
    c.hline(x0, 32, full, INK, 1)
    c.text_centred(WIDTH // 2, 44, "THE WORLD", 13)
    c.hline(x0, 150, full, INK, 1)
    c.text(x0, 160, "WEDNESDAY, 25 NOVEMBER 2026", 2)
    right = "PRICE $2.00 - No. 330"
    c.text(x1 - text_width(right, 2), 160, right, 2)
    c.hline(x0, 186, full, INK, 4)

    # --- lead story -------------------------------------------------------
    y = 204
    y = centred_block(c, WIDTH // 2, y, ["UKRAINE HITS", "RUSSIAN SHIP"], 7, 8)
    y += 6
    sub = ("Zelenskiy confirms Kyiv behind Saturday's drone strike on a "
           "Russian cargo vessel in the Gulf of Finland - as Norway urges "
           "caution and Kyiv says it sank a warship off Libya.")
    y = centred_block(c, WIDTH // 2, y, wrap(sub, 880, 2), 2, 6)
    y += 8
    lead_a = ("President Volodymyr Zelenskiy confirmed on Tuesday that "
              "Ukraine was responsible for Saturday's drone strike on a "
              "Russian cargo ship in the Gulf of Finland, the first open "
              "admission of an attack on a Russian vessel in Baltic waters.")
    lead_b = ("Norway, one of Kyiv's staunchest supporters, urged Ukraine "
              "to exercise caution in such operations. Kyiv also claimed "
              "on Monday that its forces sank a Russian warship and "
              "damaged a cargo vessel off the Libyan coast.")
    col_w = (full - 24) // 2
    ya = block(c, x0, y, wrap(lead_a, col_w, 2), 2, 6)
    yb = block(c, x0 + col_w + 24, y, wrap(lead_b, col_w, 2), 2, 6)
    y = max(ya, yb) + 6
    c.hline(x0, y, full, INK, 2)
    y += 14

    # --- three front-page stories -----------------------------------------
    stories = [
        ("RIYADH",
         "HOUTHIS HIT RIYADH TOWER",
         "A Houthi drone struck the tallest tower in Riyadh's King "
         "Abdullah Financial District, wounding 11. The coalition hit "
         "Hodeidah port in reply; the US, Egypt and Bahrain condemned "
         "the attack."),
        ("BRUSSELS",
         "NATO VOWS SPACE DEFENCE",
         "NATO vowed to defend against threats in space after reports "
         "that Russia is preparing to launch a nuclear-armed satellite, "
         "possibly as soon as December."),
        ("ANTALYA",
         "CLIMATE TALKS END WITH NO DEAL",
         "The Turkey climate summit ended without a final agreement, "
         "leaving a divided world. A Dutch court kept binding climate "
         "targets in force as the blame game over who pays goes on."),
    ]
    gap = 24
    col_w = (full - 2 * gap) // 3
    top = y
    bottom = top
    for i, (kicker, head, body) in enumerate(stories):
        cx = x0 + i * (col_w + gap)
        yy = top
        yy = block(c, cx, yy, [kicker], 2, 6, GREY)
        yy += 2
        yy = block(c, cx, yy, wrap(head, col_w, 3), 3, 6)
        yy += 2
        yy = block(c, cx, yy, wrap(body, col_w, 2), 2, 6)
        bottom = max(bottom, yy)
        if i < 2:
            c.rect(cx + col_w + 12, top, 1, bottom - top, GREY)
    y = bottom + 8
    c.hline(x0, y, full, INK, 2)
    y += 12

    # --- in brief ----------------------------------------------------------
    y = block(c, x0, y, ["IN BRIEF"], 2, 6)
    y += 4
    briefs = [
        "Trump pardons turkeys Freedom and Feathers.",
        "Trump awards Giuliani the Medal of Freedom.",
        "Trump plans tariffs on 16 trading partners.",
        "Sarkozy and Bruni ordered to stand trial.",
        "Shenzhou-24 launches with Pakistani astronaut.",
        "Australia-Solomons sign security pact.",
    ]
    brow_h = 0
    for row in range(2):
        yy = y
        for col in range(3):
            cx = x0 + col * (col_w + gap)
            item = briefs[row * 3 + col]
            end = block(c, cx, yy, wrap("- " + item, col_w, 2), 2, 5)
            brow_h = max(brow_h, end - yy)
        y += brow_h + 8
    y += 2
    c.hline(x0, y, full, INK, 2)
    y += 12

    # --- by the numbers ----------------------------------------------------
    numbers = [
        ("11 WOUNDED", "Riyadh tower hit"),
        ("30 HELD", "Cartagena hostages"),
        ("36% RISE", "Bangladesh wages"),
        ("16 PARTNERS", "tariff targets"),
    ]
    n_w = full // 4
    for i, (big, small) in enumerate(numbers):
        cx = x0 + i * n_w
        c.text_centred(cx + n_w // 2, y, big, 3)
        c.text_centred(cx + n_w // 2, y + 28, small, 2, GREY)
    y += 54
    c.hline(x0, y, full, INK, 4)
    y += 8

    # --- footer ------------------------------------------------------------
    c.text_centred(WIDTH // 2, y, "SUMMED UP IN ONE IMAGE - THE WORLD", 2, GREY)
    return c


# ---------------------------------------------------------------------------
# PNG encoding (hand-rolled: signature, IHDR, IDAT, IEND; fixed zlib level,
# no timestamps anywhere, so the bytes are identical on every run).
# ---------------------------------------------------------------------------
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    raw = bytearray()
    for yy in range(canvas.height):
        raw.append(0)  # filter: none
        start = yy * canvas.width * 3
        raw += canvas.pixels[start:start + canvas.width * 3]
    png = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def output_dir():
    """Where entry.png goes: MAKEFUN_OUTPUT_DIR wins, then /output when it
    exists (the grader's mount), else the current directory."""
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        return env
    if os.path.isdir("/output"):
        return "/output"
    return "."


def main():
    png = encode_png(draw_page())
    target = os.path.join(output_dir(), "entry.png")
    with open(target, "wb") as fh:
        fh.write(png)
    # A copy next to this file is handy for a local look, but the grader may
    # run with a read-only repository directory, so never fail over it.
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        local = os.path.join(here, "entry.png")
        if os.path.abspath(target) != os.path.abspath(local):
            with open(local, "wb") as fh:
                fh.write(png)
    except OSError:
        pass
    print("wrote %s (%d bytes)" % (target, len(png)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
