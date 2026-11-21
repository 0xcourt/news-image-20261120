#!/usr/bin/env python3
"""news-image-20261120: one broadsheet for Friday 20 November 2026.

Draws the whole front page from scratch with the Python standard
library only: a 5x7 bitmap font stored as bitmask rows, a stylised
block world map with numbered, region-coloured markers, a lead story
(Russian missiles and a drone come down in Poland), and 20 numbered
stories in two columns across five regions. No network, no files
read, no randomness: the same bytes come out on every run.

Layout (1024x1024): masthead, lead banner, numbered world map with
a region legend, then the day's stories in two columns of ten.
Every story below is a verified report from 20 November 2026 (a few
carry the day they actually happened in their summary line when that
was the 19th); claims are labelled CLAIMED and nothing unverified
is printed. 21 stories in all: the lead plus 20 numbered stories.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (20, 20, 20)
RED = (176, 30, 30)
GREY = (74, 74, 74)
OCEAN = (203, 221, 233)
LAND = (233, 224, 196)
MAPGREY = (96, 96, 96)
LEADBG = (244, 226, 220)
WHITE = (255, 255, 255)
# marker colours by region
C_EUROPE = (38, 84, 160)
C_ASIA = (34, 139, 60)
C_AFRICA = (176, 122, 20)
C_MIDEAST = (122, 62, 140)
C_AMERICAS = RED

# ---------------------------------------------------------------- font: 5x7
# Each glyph is 7 rows; each row is a 5-bit integer, bit 4 = leftmost
# column. Uppercase, digits and the punctuation the page needs.
# draw() upper-cases everything before lookup.
FONT = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b00000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110),
    " ": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b00100, 0b01000),
    ":": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000),
    ";": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b00100, 0b01000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
    "'": (0b00100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000),
    '"': (0b01010, 0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000),
    "-": (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "+": (0b00000, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0b00000),
    "=": (0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000),
    "*": (0b00000, 0b01010, 0b00100, 0b11111, 0b00100, 0b01010, 0b00000),
    "\u2022": (0b00000, 0b00000, 0b01110, 0b01110, 0b01110, 0b00000, 0b00000),
}


def glyph_width(scale):
    """Advance width of one character cell at the given scale."""
    return 5 * scale + scale


def text_width(s, scale):
    """Advance width in pixels of s at the given scale."""
    return len(s) * glyph_width(scale)


# ---------------------------------------------------------------- canvas
class Canvas:
    """An RGB pixel grid with drawing primitives."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill(0, 0, w, h, bg)

    def fill(self, x0, y0, w, h, rgb):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x0 + w)
        y1 = min(self.h, y0 + h)
        r, g, b = rgb
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x1 - x0):
                i = base + x * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def plot(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def hline(self, x0, x1, y, rgb, thick=1):
        if x1 < x0:
            x0, x1 = x1, x0
        self.fill(x0, y, x1 - x0 + 1, thick, rgb)

    def vline(self, x, y0, y1, rgb, thick=1):
        if y1 < y0:
            y0, y1 = y1, y0
        self.fill(x, y0, thick, y1 - y0 + 1, rgb)

    def seg(self, x0, y0, x1, y1, rgb, thick=1):
        """Straight line by integer interpolation, any slope."""
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        half = thick // 2
        for k in range(steps + 1):
            x = x0 + (dx * k) // steps
            y = y0 + (dy * k) // steps
            self.fill(x - half, y - half, thick, thick, rgb)

    def dot(self, cx, cy, r, rgb):
        """Filled disc of radius r."""
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r:
                    self.plot(x, y, rgb)

    def halo(self, cx, cy, r, rgb, thick=2):
        """Disc outline: ring of thickness thick."""
        for y in range(cy - r - thick, cy + r + thick + 1):
            for x in range(cx - r - thick, cx + r + thick + 1):
                d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy)
                if (r - thick) * (r - thick) <= d2 <= (r + thick) * (r + thick):
                    self.plot(x, y, rgb)

    def burst(self, cx, cy, r, rgb):
        """Eight-pointed star: two stacked diamonds."""
        half = int(r * 0.62)
        for dy in range(-r, r + 1):
            spread = r - abs(dy)
            self.hline(cx - spread, cx + spread, cy + dy, rgb)
        for dy in range(-half, half + 1):
            spread = half - abs(dy)
            self.vline(cx + dy, cy - spread, cy + spread, rgb)
            self.vline(cx - dy, cy - spread, cy + spread, rgb)

    def draw(self, s, x, y, scale, rgb, align="l"):
        """Render text; align l/c/r is relative to x. Returns end x."""
        s = s.upper()
        if align == "c":
            x -= text_width(s, scale) // 2
        elif align == "r":
            x -= text_width(s, scale)
        cx = x
        for ch in s:
            rows = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = rows[row]
                for col in range(5):
                    if (bits >> (4 - col)) & 1:
                        self.fill(cx + col * scale, y + row * scale,
                                  scale, scale, rgb)
            cx += glyph_width(scale)
        return cx


# ---------------------------------------------------------------- PNG
def _chunk(tag, payload):
    raw = struct.pack(">I", len(payload)) + tag + payload
    return raw + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)


def encode_png(cv):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    rows = bytearray()
    for y in range(cv.h):
        rows.append(0)
        rows += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    idat = zlib.compress(bytes(rows), 9)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


# ---------------------------------------------------------------- world map
MAP_X, MAP_Y, MAP_W, MAP_H = 24, 226, 976, 240
MAP_LON0, MAP_LON1 = -180.0, 180.0
MAP_LAT0, MAP_LAT1 = 78.0, -56.0


def to_xy(lon, lat):
    x = MAP_X + int((lon - MAP_LON0) / (MAP_LON1 - MAP_LON0) * MAP_W)
    y = MAP_Y + int((MAP_LAT0 - lat) / (MAP_LAT0 - MAP_LAT1) * MAP_H)
    return x, y


# Stylised continents as (lon0, lat0, lon1, lat1) blocks: lon0 < lon1,
# lat0 < lat1. Rough coastlines are fine; the markers carry the map.
LAND_RECTS = [
    # North America
    (-168, 60, -140, 70), (-140, 48, -60, 70), (-125, 25, -66, 48),
    (-117, 14, -86, 25), (-92, 8, -77, 15), (-55, 60, -20, 76),
    (-80, 20, -74, 23), (-61, 12, -60, 14),
    # South America
    (-79, 0, -52, 10), (-75, -15, -42, 0), (-70, -35, -55, -15),
    (-70, -52, -62, -35),
    # Europe
    (-10, 36, 3, 44), (-5, 44, 30, 58), (5, 55, 30, 70),
    (-5, 50, 2, 58), (8, 36, 28, 45), (-10, 51, -6, 55), (-22, 63, -14, 66),
    # Africa
    (-10, 15, 35, 32), (-8, 0, 42, 15), (12, -18, 33, 0),
    (16, -35, 32, -18), (43, -25, 50, -12),
    # Asia
    (30, 50, 180, 72), (45, 42, 130, 52), (78, 20, 125, 42),
    (68, 8, 88, 32), (95, 5, 105, 28), (35, 12, 58, 30),
    (130, 30, 142, 45), (140, 41, 145, 45), (95, -8, 140, 5),
    (131, -9, 147, -1), (126, 34, 130, 40), (120, 22, 122, 25),
    (120, 6, 122, 18), (80, 6, 82, 9),
    # Oceania
    (113, -25, 130, -12), (128, -38, 148, -12), (146, -39, 153, -30),
    (166, -47, 178, -34),
]

MAP_LABELS = [
    (-100, 60, "NORTH AMERICA"), (-60, -20, "SOUTH AMERICA"),
    (20, 5, "AFRICA"), (92, 58, "ASIA"),
    (134, -28, "AUSTRALIA"), (-150, 8, "PACIFIC"),
    (-35, 22, "ATLANTIC"), (78, -32, "INDIAN OCEAN"),
]

# num, lon, lat, label dx, label dy, colour. Dots for The Hague,
# Brussels, Cardiff and Kyiv are nudged a few degrees so the crowded
# north-west corner of Europe stays legible; the EUROPE continent
# label is left off because that corner has no clear space for it.
MARKERS = [
    (1, 23.0, 50.3, -28, -8, RED),          # Poland - lead star
    (2, 31.5, 50.5, 10, -8, C_EUROPE),      # Kyiv
    (3, 2.3, 48.9, -32, 10, C_EUROPE),      # Paris
    (4, -2.0, 56.0, -34, -20, C_EUROPE),    # The Hague
    (5, 8.5, 50.5, 10, 14, C_EUROPE),       # Brussels
    (6, 28.2, 60.5, 10, -8, C_EUROPE),      # Narva
    (7, 116.4, 39.9, 10, -8, C_ASIA),       # Beijing
    (8, 46.7, 24.7, 10, -8, C_MIDEAST),     # Riyadh
    (9, 34.5, 31.5, -34, 10, C_MIDEAST),    # Gaza
    (10, 56.5, 26.5, 10, 12, C_MIDEAST),    # Hormuz
    (11, -74.0, 40.7, 10, -8, C_AMERICAS),  # New York
    (12, -80.2, 25.8, -34, 8, C_AMERICAS),  # Miami
    (13, -122.4, 37.8, -34, -8, C_AMERICAS),  # San Francisco
    (14, 125.8, 39.0, 10, 12, C_ASIA),      # Pyongyang
    (15, 139.7, 35.7, 10, -8, C_ASIA),      # Tokyo
    (16, 77.2, 28.6, 10, -8, C_ASIA),       # New Delhi
    (17, -76.3, -10.7, 10, -8, C_AMERICAS),  # Cerro de Pasco
    (18, -118.2, 34.1, 10, 12, C_AMERICAS),  # Los Angeles
    (19, -9.0, 52.0, -40, -8, C_EUROPE),    # Cardiff
    (20, 2.2, 41.4, -36, 16, C_EUROPE),     # Barcelona
    (21, 28.0, -26.2, 10, -8, C_AFRICA),    # Johannesburg
]

LEGEND = [
    (C_EUROPE, "EUROPE"), (C_ASIA, "ASIA"), (C_MIDEAST, "MIDDLE EAST"),
    (C_AMERICAS, "AMERICAS"), (C_AFRICA, "AFRICA"), (RED, "LEAD STORY"),
]

# ---------------------------------------------------------------- stories
# (number, headline, summary) - every line fits 38 chars at scale 2.
STORIES = [
    (2, "KYIV BRIDGES HIT IN BIGGEST STRIKE",
     "27 BALLISTIC, 84 CRUISE, 404 DRONES"),
    (3, "FRANCE CALLS UN SECURITY COUNCIL",
     "AUSTRIAN, DUTCH EMBASSIES DAMAGED"),
    (4, "ICJ: MYANMAR COMMITTED GENOCIDE",
     "ROHINGYA RULING THU; MYANMAR REJECTS"),
    (5, "UK AND EU SIGN RESET DEAL",
     "FOOD, CARBON, YOUTH MOBILITY AGREED"),
    (6, "ESTONIA SHUTS RUSSIA BORDER",
     "ROAD CROSSINGS CLOSE FROM 1 DEC"),
    (7, "TRUMP, XI, PUTIN MEET IN CHINA",
     "PUTIN INVITES EUROPE TO MOSCOW"),
    (8, "HOUTHI MISSILE HITS RIYADH TOWER",
     "PIF TOWER HIT THU; MORE ALERTS FRI"),
    (9, "ISRAELI STRIKES KILL 6 IN GAZA",
     "CEASEFIRE STRAINED; 1,600+ DEAD SINCE"),
    (10, "TANKERS HIT MINES AT HORMUZ",
     "IRGC CLAIM, UNVERIFIED; BRENT $92"),
    (11, "S&P 500 SINKS 3.7% INTO CORRECTION",
     "7TH STRAIGHT DOWN DAY; NASDAQ -5.3%"),
    (12, "BITCOIN BELOW $62,000",
     "LOWEST SINCE JULY; NEAR $61,700"),
    (13, "ANTHROPIC SHARES SLIDE 9%",
     "RECORD $81.3BN IPO; DAY ONE +17%"),
    (14, "BINANCE HACKERS MOVE $594M ETH",
     "N. KOREA-LINKED; VIA THORCHAIN"),
    (15, "JAPAN CORE INFLATION HITS 2.2%",
     "YEAR HIGH; ENERGY SUBSIDIES ENDED"),
    (16, "PAKISTAN MINISTER VISITS DELHI",
     "FIRST SINCE 2025 CONFLICT; SCO MEET"),
    (17, "PERU QUAKE 6.7 SHAKES ANDES",
     "FELT IN LIMA; NO DAMAGE REPORTED"),
    (18, "PALISADES FIRE ARSON VERDICT",
     "RINDERKNECHT GUILTY ON 2 COUNTS"),
    (19, "LAUREN PRICE UNDISPUTED CHAMPION",
     "FIRST WELSH BOXER TO HOLD ALL 4"),
    (20, "CANCER PILL SHRINKS TUMOURS",
     "44% OF PANCREATIC PATIENTS RESPOND"),
    (21, "MLAMBO-NGCUKA DIES",
     "EX-SA DEPUTY PRESIDENT, UN WOMEN"),
]


# ---------------------------------------------------------------- the page
def build():
    cv = Canvas(W, H, PAPER)
    # outer frame
    cv.fill(8, 8, W - 16, 4, INK)
    cv.fill(8, H - 12, W - 16, 4, INK)
    cv.fill(8, 8, 4, H - 16, INK)
    cv.fill(W - 12, 8, 4, H - 16, INK)

    # masthead
    cv.draw("THE WORLD IN ONE PICTURE", 512, 22, 5, INK, "c")
    cv.hline(24, 1000, 64, INK, 3)
    cv.hline(24, 1000, 67, INK, 1)
    cv.draw("FRIDAY 20 NOVEMBER 2026  \u2022  21 STORIES  \u2022  5 REGIONS",
            512, 74, 2, INK, "c")

    # lead banner
    cv.fill(24, 100, 976, 104, LEADBG)
    cv.fill(24, 100, 8, 104, RED)
    cv.draw("LEAD STORY  \u2022  MISSILES LAND IN A NATO STATE",
            48, 106, 2, RED)
    cv.draw("RUSSIAN MISSILES HIT POLAND", 48, 124, 5, RED)
    cv.draw("NATO: GRAVE VIOLATION; WARSAW: PROVOCATION", 48, 162, 3, INK)
    cv.draw("2 MISSILES + 1 DRONE DOWN IN SE POLAND; NO INJURIES",
            48, 186, 2, GREY)

    # map title
    cv.draw("THE WORLD, NUMBERED - FOLLOW THE NUMBERS", 24, 210, 2, INK)
    cv.draw("STAR 1 IS THE LEAD STORY", 1000, 210, 2, RED, "r")

    # map: ocean, land, border, labels, markers
    cv.fill(MAP_X, MAP_Y, MAP_W, MAP_H, OCEAN)
    for lon0, lat0, lon1, lat1 in LAND_RECTS:
        x0, y0 = to_xy(lon0, lat1)
        x1, y1 = to_xy(lon1, lat0)
        cv.fill(x0, y0, x1 - x0, y1 - y0, LAND)
    cv.fill(MAP_X, MAP_Y, MAP_W, 2, INK)
    cv.fill(MAP_X, MAP_Y + MAP_H - 2, MAP_W, 2, INK)
    cv.fill(MAP_X, MAP_Y, 2, MAP_H, INK)
    cv.fill(MAP_X + MAP_W - 2, MAP_Y, 2, MAP_H, INK)
    for lon, lat, name in MAP_LABELS:
        x, y = to_xy(lon, lat)
        cv.draw(name, x, y, 2, MAPGREY, "c")
    for num, lon, lat, dx, dy, colour in MARKERS:
        x, y = to_xy(lon, lat)
        if num == 1:
            cv.burst(x, y, 13, RED)
            cv.halo(x, y, 17, RED, 2)
        else:
            cv.halo(x, y, 6, colour, 2)
            cv.dot(x, y, 4, colour)
        lx, ly = x + dx, y + dy
        if abs(dx) > 12 or abs(dy) > 12:
            cv.seg(x, y, lx + 6, ly + 7, colour, 1)
        cv.draw(str(num), lx, ly, 2, colour)

    # region legend, spread evenly across the page
    widths = [12 + 6 + text_width(name, 2) for _, name in LEGEND]
    gap = (976 - sum(widths)) // (len(LEGEND) - 1)
    lx = 24
    for (colour, name), w in zip(LEGEND, widths):
        cv.dot(lx + 6, 481, 5, colour)
        cv.draw(name, lx + 18, 474, 2, INK)
        lx += w + gap

    # stories header
    cv.hline(24, 1000, 496, INK, 2)
    cv.draw("THE DAY IN STORIES", 24, 504, 3, INK)
    cv.draw("NUMBERS MATCH THE MAP", 1000, 507, 2, GREY, "r")

    # stories grid: two columns of ten
    colour_of = {num: colour for num, *_rest, colour in MARKERS}
    y0, row_h = 530, 46
    for i, (num, head, summ) in enumerate(STORIES):
        col = i // 10
        row = i % 10
        x = 24 + col * 488
        y = y0 + row * row_h
        if text_width(head, 2) > 456 or text_width(summ, 2) > 456:
            raise ValueError("story %d line too wide: %r" % (num, head))
        cv.fill(x, y, 24, 24, colour_of[num])
        cv.draw(str(num), x + 12, y + 5, 2, WHITE, "c")
        cv.draw(head, x + 32, y + 2, 2, INK)
        cv.draw(summ, x + 32, y + 19, 2, GREY)
        if row < 9:
            cv.hline(x, x + 456, y + 33, (200, 195, 185), 1)

    # footer
    cv.hline(24, 1000, 990, INK, 2)
    cv.draw("EVERY STORY ABOVE HAPPENED OR WAS FIRST REPORTED "
            "ON FRIDAY 20 NOVEMBER 2026", 512, 996, 2, INK, "c")
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    png = encode_png(build())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))


if __name__ == "__main__":
    main()
