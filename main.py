#!/usr/bin/env python3
"""THE WORLD — front page for Wednesday, 25 November 2026.

Deterministic, stdlib-only newspaper front-page renderer. Draws a 1024x1024
PNG broadsheet summing up the day's world news and writes it to entry.png.
No network, no clock, no randomness: the same input always yields the same
bytes. Output goes to MAKEFUN_OUTPUT_DIR if set, else /output when it
exists, else the current directory. A best-effort copy next to this script
is attempted but never allowed to fail the run (the grader's repo dir is
read-only).
"""

import os
import struct
import sys
import zlib

PAGE_W = 1024
PAGE_H = 1024
INK = (18, 18, 18)
PAPER = (250, 247, 238)
GREY = (110, 108, 100)
RULE = (40, 40, 40)


# ---------------------------------------------------------------- font ----
# Each glyph is seven rows of five cells; '#' is ink, '.' is blank.
# Hand-drawn for this page; only the characters the page actually uses.
GLYPHS = {
    "A": ("..#..", ".#.#.", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.#.#", "#.##."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "&": (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
}

CELL_W = 6  # glyph advance in font units (5 px + 1 px gap)


def clean(text):
    """Upper-case the text and swap any unsupported char for a space."""
    out = []
    for ch in text.upper():
        out.append(ch if ch in GLYPHS else " ")
    return "".join(out)


def text_width(text, scale):
    return len(clean(text)) * CELL_W * scale - scale


# -------------------------------------------------------------- canvas ----
class Sheet:
    """An RGB pixel buffer with simple drawing helpers."""

    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        self.pixels = bytearray(colour * (width * height))

    def set_px(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = bytes(colour)

    def fill(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.pixels[i:i + len(row)] = row

    def hline(self, x, y, w, colour=INK, thick=1):
        self.fill(x, y, w, thick, colour)

    def vline(self, x, y, h, colour=INK, thick=1):
        self.fill(x, y, thick, h, colour)

    def frame(self, x, y, w, h, colour=INK, thick=1):
        self.hline(x, y, w, colour, thick)
        self.hline(x, y + h - thick, w, colour, thick)
        self.vline(x, y, h, colour, thick)
        self.vline(x + w - thick, y, h, colour, thick)

    def glyph(self, x, y, ch, scale, colour):
        rows = GLYPHS.get(ch, GLYPHS[" "])
        for ry, row in enumerate(rows):
            for rx, cell in enumerate(row):
                if cell == "#":
                    self.fill(x + rx * scale, y + ry * scale,
                              scale, scale, colour)

    def text(self, x, y, raw, scale, colour=INK):
        cx = x
        for ch in clean(raw):
            self.glyph(cx, y, ch, scale, colour)
            cx += CELL_W * scale
        return cx

    def centred(self, y, raw, scale, colour=INK, cx=PAGE_W // 2):
        w = text_width(raw, scale)
        return self.text(cx - w // 2, y, raw, scale, colour)


def wrap(raw, scale, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = clean(raw).split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def paragraph(sheet, x, y, raw, scale, max_w, leading, colour=INK):
    """Draw a wrapped paragraph; returns the y just below the last line."""
    for line in wrap(raw, scale, max_w):
        sheet.text(x, y, line, scale, colour)
        y += leading
    return y


# ---------------------------------------------------------------- png ------
def write_png(sheet, path):
    raw = bytearray()
    stride = sheet.width * 3
    for yy in range(sheet.height):
        raw.append(0)  # filter: none
        start = yy * stride
        raw += sheet.pixels[start:start + stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", sheet.width, sheet.height, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n"
    blob += chunk(b"IHDR", ihdr)
    blob += chunk(b"IDAT", comp)
    blob += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)


# -------------------------------------------------------------- content ----
DATE_LINE = "WEDNESDAY, 25 NOVEMBER 2026"
MASTHEAD = "THE WORLD"

LEAD_KICKER = "WAR AT SEA  *  UKRAINE STRIKES FAR FROM HOME"
LEAD_HEAD = "UKRAINE SINKS RUSSIAN WARSHIP OFF LIBYA"
LEAD_SUB = ("Kyiv says sea drones destroyed the corvette Merkury at Benghazi "
            "and hit a cargo ship in the Gulf of Finland")
LEAD_BODY = (
    "Ukraine said on Tuesday that its naval drones sank the Russian missile "
    "corvette Merkury in the Libyan port of Benghazi and struck the cargo "
    "vessel Sparta II in the Gulf of Finland. Kyiv called the Benghazi "
    "strike lawful self-defence. Moscow vowed what President Vladimir "
    "Putin called inevitable retaliation, while Norway urged caution."
)

STORIES = [
    {
        "kicker": "MARKETS",
        "head": "NVIDIA TUMBLES AS AI BOOM DOUBTS SPREAD",
        "body": (
            "Nvidia shares fell about 7 percent on Tuesday, a day after the "
            "board brought back Jensen Huang as chief executive. Investors "
            "are again asking whether the AI boom can pay for itself."
        ),
    },
    {
        "kicker": "MIDDLE EAST",
        "head": "MINES HIT TANKERS IN STRAIT OF HORMUZ",
        "body": (
            "Iran's Revolutionary Guards said oil tankers under American air "
            "escort struck naval mines in the Strait of Hormuz, the passage "
            "for a fifth of the world's oil. A tower in Riyadh was hit and "
            "11 people were hurt."
        ),
    },
    {
        "kicker": "ASIA",
        "head": "FACTORY FIRE IN INDONESIA KILLS 26",
        "body": (
            "At least 26 workers died after fire swept through a candy "
            "factory in Cikande, Banten province, west of Jakarta. Rescue "
            "teams searched the burned-out plant as families waited outside "
            "for news of their loved ones."
        ),
    },
]

BRIEFS = [
    "SARKOZY TO FACE TRIAL: French judges order the former president and "
    "his wife Carla Bruni to trial, with a first hearing on 1 April 2027.",
    "HOSTAGES IN CARTAGENA: Armed men held about 20 people in a "
    "supermarket in the Colombian port city before police moved in.",
    "PAKISTAN IN ORBIT: Pakistan's first astronaut reached China's space "
    "station, a milestone for the country's space programme.",
    "SENEGAL CHAMPIONS AGAIN: Senegal regained the Africa Cup of Nations "
    "title after sport's highest court ruled in its favour.",
]

NUMBERS = [
    ("2.76%", "NIKKEI FALL ON TUESDAY"),
    ("7%", "NVIDIA SHARES DROP"),
    ("26", "WORKERS KILLED IN BANTEN"),
    ("11", "WOUNDED IN RIYADH HIT"),
]


# -------------------------------------------------------------- layout ----
MARGIN = 40
CONTENT_W = PAGE_W - 2 * MARGIN


def draw(sheet):
    sheet.fill(0, 0, PAGE_W, PAGE_H, PAPER)

    # --- masthead ------------------------------------------------------
    sheet.centred(26, MASTHEAD, 12)
    sheet.hline(MARGIN, 122, CONTENT_W, RULE, 4)
    sheet.centred(134, DATE_LINE, 2)
    sheet.text(MARGIN, 134, "NO. 329", 2, GREY)
    right = "PRICE: ONE DOLLAR"
    sheet.text(PAGE_W - MARGIN - text_width(right, 2), 134, right, 2, GREY)
    sheet.hline(MARGIN, 160, CONTENT_W, RULE, 2)

    # --- lead story ----------------------------------------------------
    y = 176
    sheet.centred(y, LEAD_KICKER, 2, GREY)
    y += 30
    for line in wrap(LEAD_HEAD, 4, CONTENT_W):
        sheet.centred(y, line, 4)
        y += 36
    y += 6
    for line in wrap(LEAD_SUB, 2, CONTENT_W):
        sheet.centred(y, line, 2, GREY)
        y += 19
    y += 12
    y = paragraph(sheet, MARGIN, y, LEAD_BODY, 2, CONTENT_W, 19)
    y += 8
    sheet.hline(MARGIN, y, CONTENT_W, RULE, 2)
    y += 12

    # --- three front-page stories --------------------------------------
    gap = 24
    col_w = (CONTENT_W - 2 * gap) // 3
    col_tops = []
    for idx, story in enumerate(STORIES):
        x = MARGIN + idx * (col_w + gap)
        cy = y
        sheet.text(x, cy, story["kicker"], 2, GREY)
        cy += 22
        for line in wrap(story["head"], 2, col_w):
            sheet.text(x, cy, line, 2)
            cy += 18
        cy += 6
        cy = paragraph(sheet, x, cy, story["body"], 2, col_w, 16)
        col_tops.append(cy)
    col_h = max(col_tops) - y
    for idx in range(2):
        x = MARGIN + idx * (col_w + gap)
        sheet.vline(x + col_w + gap // 2, y, col_h, GREY, 1)
    y = max(col_tops) + 6
    sheet.hline(MARGIN, y, CONTENT_W, RULE, 2)
    y += 10

    # --- in brief ------------------------------------------------------
    sheet.text(MARGIN, y, "IN BRIEF", 2)
    sheet.hline(MARGIN + text_width("IN BRIEF", 2) + 12, y + 7,
                CONTENT_W - text_width("IN BRIEF", 2) - 12, GREY, 1)
    y += 26
    brief_w = (CONTENT_W - 32) // 2
    brief_bottom = y
    for half in range(2):
        bx = MARGIN + half * (brief_w + 32)
        by = y
        for item in BRIEFS[half * 2:half * 2 + 2]:
            sheet.text(bx, by, "*", 2)
            by = paragraph(sheet, bx + 24, by, item, 2, brief_w - 24, 16)
            by += 4
        brief_bottom = max(brief_bottom, by)
    y = brief_bottom + 4
    sheet.hline(MARGIN, y, CONTENT_W, RULE, 2)
    y += 10

    # --- by the numbers -------------------------------------------------
    sheet.text(MARGIN, y, "BY THE NUMBERS", 2)
    sheet.hline(MARGIN + text_width("BY THE NUMBERS", 2) + 12, y + 7,
                CONTENT_W - text_width("BY THE NUMBERS", 2) - 12, GREY, 1)
    y += 22
    box_w = (CONTENT_W - 3 * 16) // 4
    box_h = 80
    for idx, (num, label) in enumerate(NUMBERS):
        x = MARGIN + idx * (box_w + 16)
        sheet.frame(x, y, box_w, box_h, RULE, 2)
        sheet.centred(y + 8, num, 3, INK, cx=x + box_w // 2)
        ly = y + 36
        for line in wrap(label, 2, box_w - 20):
            sheet.centred(ly, line, 2, GREY, cx=x + box_w // 2)
            ly += 14
    y += box_h + 10

    # --- footer ---------------------------------------------------------
    sheet.hline(MARGIN, y, CONTENT_W, RULE, 2)
    y += 10
    sheet.centred(y, "THE WORLD  *  WEDNESDAY, 25 NOVEMBER 2026", 2, GREY)
    assert y + 20 <= PAGE_H - 20, "layout overflowed the page"


def pick_output_dir():
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        return env
    if os.path.isdir("/output"):
        return "/output"
    return os.getcwd()


def main():
    sheet = Sheet(PAGE_W, PAGE_H, PAPER)
    draw(sheet)
    out_dir = pick_output_dir()
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    write_png(sheet, target)
    # Best-effort copy next to this script; the grader's repo dir is
    # read-only, so a failure here must never fail the run.
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        local = os.path.join(here, "entry.png")
        if os.path.abspath(target) != os.path.abspath(local):
            with open(target, "rb") as src:
                data = src.read()
            with open(local, "wb") as dst:
                dst.write(data)
    except OSError:
        pass
    print("wrote %s (%d bytes)" % (target, os.path.getsize(target)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
