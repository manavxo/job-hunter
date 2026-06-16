import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import csv

# ── STYLES ────────────────────────────────────────────────────────────────────
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
GREEN       = PatternFill("solid", fgColor="C6EFCE")
YELLOW      = PatternFill("solid", fgColor="FFEB9C")
RED         = PatternFill("solid", fgColor="FFC7CE")
BLUE_LIGHT  = PatternFill("solid", fgColor="DDEEFF")

HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
BOLD        = Font(bold=True)
WRAP        = Alignment(wrap_text=True, vertical="top")
CENTER      = Alignment(horizontal="center", vertical="center", wrap_text=True)

thin = Side(border_style="thin", color="BBBBBB")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

SCORE_FILL = {
    5: PatternFill("solid", fgColor="00B050"),
    4: PatternFill("solid", fgColor="92D050"),
    3: PatternFill("solid", fgColor="FFEB9C"),
    2: PatternFill("solid", fgColor="FF9900"),
    1: PatternFill("solid", fgColor="FF0000"),
}

# ── BUSINESS DATA ─────────────────────────────────────────────────────────────
# Columns:
# #, Store Name, Type, Address, Phone, Hours, Distance from E Broadway & Renfrew,
# Open Tomorrow AM (Tue Jun 17), What They Buy/Sell/Trade, Trade Score (1–5), Notes

businesses = [
    (1,
     "The Hackery",
     "Used Computer Store",
     "304 Victoria Drive, Vancouver BC V5L 4C7",
     "(778) 373-8295",
     "Tue–Sat: 11am – 6pm\nClosed Mon & Sun",
     "~1.5 km (CLOSEST)",
     "YES – opens 11am",
     "Refurbished PCs & Mac; buys/sells desktops, laptops, monitors, parts; knowledgeable staff",
     4,
     "Right in East Van — walk or quick bus from your area. Call ahead (778) 373-8295 to ask about RTX desktop tower inventory before visiting. Website: thehackery.ca"),

    (2,
     "A-1 Trade & Loan",
     "Pawn Shop",
     "2641 Commercial Drive, Vancouver BC V5N 4C3",
     "(604) 875-8005",
     "Mon–Sat: 10am – 4pm\nClosed Sun",
     "~1 km (VERY CLOSE)",
     "YES – opens 10am",
     "Vancouver's oldest pawnshop (est. 1991); buys/sells electronics, gaming consoles, laptops",
     3,
     "On Commercial Drive — extremely close. Note: CLOSES AT 4PM so go in the morning. Ask if they have gaming PC towers in stock. Negotiable on bundles."),

    (3,
     "PayMore Vancouver",
     "Electronics Buy/Sell/Trade",
     "4534 Main Street, Vancouver BC V5V 3R5\n(near E 29th Ave)",
     "N/A (no public phone listed — visit in person or DM on Instagram)",
     "Mon–Sat: 11am – 7pm\nSun: 10am – 6pm",
     "~3.5 km",
     "YES – opens 11am",
     "Dedicated electronics trade-in store; buys/sells/trades gaming PCs, PS5, consoles, laptops, phones",
     5,
     "Core business model is exactly what you need. Bring PS5 + Yoga and ask for a bundle trade quote. May have gaming desktop towers in store. Instagram: @paymorestores"),

    (4,
     "pcbuy.ca (PCBUY)",
     "Used & Custom PC Store (Appt Only)",
     "1868 Glen Drive, Vancouver BC V6A 4K4",
     "(778) 378-5019\ninfo@pcbuy.ca",
     "Mon–Sat (appointment required)\nCall to book",
     "~4 km",
     "CALL TO BOOK – appointment required",
     "New & used custom PCs; formal GPU/computer trade-in program; old hardware → cash or store credit",
     4,
     "Has an explicit trade-in program. Call (778) 378-5019 ASAP or email info@pcbuy.ca to book for tomorrow. Facebook: PCBUY Downtown Vancouver. Best option for trading Yoga Slim 7 for PC credit."),

    (5,
     "PC Galore",
     "Used Computer Store",
     "2744 W 4th Avenue, Vancouver BC V6K 1R1\n(Kitsilano)",
     "(604) 732-7816",
     "Mon–Sat: 10am – 6pm\nClosed Sun",
     "~7 km",
     "YES – opens 10am",
     "Laptops, desktops, accessories; buys and trades used computers; accepts most laptops/desktops meeting min specs",
     4,
     "Vancouver's oldest used computer store (est. 1994, 30+ years). High credibility. Ask about gaming desktop inventory with RTX cards. Instagram: @pcgalore | Site: pcgalore.com"),

    (6,
     "Metro PawnBrokers",
     "Pawn Shop",
     "4939 Kingsway, Burnaby BC V5H 2E5",
     "(604) 451-5626",
     "Mon–Sat: 9:30am – 6pm\nClosed Sun",
     "~6 km",
     "YES – opens 9:30am",
     "Buys/sells gaming consoles (PlayStation, Xbox, Nintendo), electronics, laptops; family-owned",
     3,
     "Explicitly stocks PlayStation gear. Family-owned = more flexible on bundle deals. Call ahead to ask about gaming PC towers. Located near Metrotown."),

    (7,
     "Computer 101",
     "PC Repair & Build Shop",
     "Vancouver BC (exact address not publicly listed)\nCall for location",
     "(604) 901-9799\ncomputer101.ca",
     "Mon–Sat: 10am – 7pm",
     "Unknown (call first)",
     "YES – opens 10am (call for address)",
     "PC repair, custom PC builds, PS5 repair, MacBook/laptop repair; serves all Metro Vancouver",
     2,
     "Does PS5 repairs = understands PS5 value well. Call (604) 901-9799 to ask if they have any used gaming desktop towers for sale and if they accept trade-ins. No walk-in without confirming address."),

    (8,
     "SoneXPC (Sonex Computer)",
     "Custom PC Builder",
     "#1035 – 8766 McKim Way, Richmond BC V6X 4G4",
     "(604) 717-6111",
     "Mon–Sat: 10am – 6pm\nClosed Sun",
     "~16 km (Richmond)",
     "YES – opens 10am",
     "Custom-built gaming PCs; carries RTX 5060Ti, 5070, 5070Ti; primarily new builds",
     2,
     "Primarily a new PC builder — less likely to do used-hardware bundle swaps. Better to sell PS5/laptop separately and use cash here if needed. Instagram: @sonexpc"),

    (9,
     "Roath's Pawn Shop",
     "Pawn Shop",
     "13573 King George Blvd, Surrey BC V3T 2V1",
     "(604) 584-4010",
     "Mon–Fri: 9am – 6pm\nSat: 9am – 5pm\nClosed Sun",
     "~22 km (Surrey)",
     "YES – opens 9am",
     "Pawn/buy/sell electronics, jewelry, gaming consoles; carries some tech items",
     2,
     "Far from East Van (~50 min transit). Primarily jewelry + general electronics. No specific mention of gaming desktop towers. Lower priority than closer options. Call first before making the trip."),

    (10,
     "A-Z Video Games",
     "Video Game Store",
     "748 Broadway E #102, Vancouver BC V5T 1X9",
     "(604) 874-3919",
     "⚠️ APPEARS CLOSED (Yelp: marked CLOSED)",
     "~2 km",
     "NO – likely permanently closed",
     "Used to buy/sell/trade video games; no gaming PC inventory",
     1,
     "RED FLAG: Marked as CLOSED on Yelp as of 2026. Even if open, they focused on game titles not PC hardware. Do not visit without calling ahead to confirm they're still operating."),
]

COLUMNS = [
    "#",
    "Store Name",
    "Type",
    "Address",
    "Phone / Email",
    "Hours",
    "Distance from\nE Broadway & Renfrew",
    "Open Tomorrow AM\n(Tue Jun 17 2026)",
    "What They Buy / Sell / Trade",
    "Trade\nScore",
    "Notes / Action",
]
COL_WIDTHS = [4, 28, 24, 36, 28, 26, 18, 20, 40, 9, 52]

# ── BUILD WORKBOOK ─────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Vancouver Businesses"

# Header
for ci, col in enumerate(COLUMNS, 1):
    c = ws.cell(1, ci, col)
    c.fill      = HEADER_FILL
    c.font      = HEADER_FONT
    c.alignment = CENTER
    c.border    = BORDER
ws.row_dimensions[1].height = 36
ws.freeze_panes = "A2"

# Data rows
for ri, biz in enumerate(businesses, 2):
    # determine row colour
    notes = biz[10].upper()
    open_tm = biz[7].upper()
    score = biz[9]

    if "RED FLAG" in notes or "CLOSED" in biz[7].upper():
        row_fill = RED
    elif score == 5:
        row_fill = GREEN
    elif "YES" in open_tm and score >= 3:
        row_fill = YELLOW
    else:
        row_fill = None

    for ci, val in enumerate(biz, 1):
        c = ws.cell(ri, ci, val)
        c.alignment = WRAP
        c.border    = BORDER
        if row_fill:
            c.fill = row_fill
        if ci == 10:           # score column
            c.fill      = SCORE_FILL.get(val, PatternFill())
            c.font      = BOLD
            c.alignment = CENTER

    ws.row_dimensions[ri].height = 80

for ci, w in enumerate(COL_WIDTHS, 1):
    ws.column_dimensions[get_column_letter(ci)].width = w

# ── LEGEND / KEY ──────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Legend")
ws2.column_dimensions["A"].width = 30
ws2.column_dimensions["B"].width = 70

legend_rows = [
    ("Colour", "Meaning"),
    ("GREEN row", "Score 5 — dedicated trade-in business; best bet"),
    ("YELLOW row", "Score 3–4 and open tomorrow morning"),
    ("RED row", "Closed / red flag / hardware below target"),
    ("Score 5", "Core business is buy/sell/trade electronics"),
    ("Score 4", "Actively buys & trades used computers"),
    ("Score 3", "Pawn shop — negotiable, worth visiting"),
    ("Score 2", "Less likely to trade; better for cash sales"),
    ("Score 1", "Not recommended"),
    ("", ""),
    ("Contact priority tomorrow", ""),
    ("9:30 AM", "Call Metro PawnBrokers (604) 451-5626"),
    ("10:00 AM", "Call A-1 Trade & Loan (604) 875-8005"),
    ("10:00 AM", "Call PC Galore (604) 732-7816"),
    ("10:00 AM", "Call/email pcbuy.ca (778) 378-5019 / info@pcbuy.ca"),
    ("11:00 AM", "Visit PayMore Vancouver (4534 Main St) with both devices"),
    ("11:00 AM", "OR visit The Hackery (304 Victoria Drive)"),
]

for ri, (a, b) in enumerate(legend_rows, 1):
    ca = ws2.cell(ri, 1, a)
    cb = ws2.cell(ri, 2, b)
    ca.font = BOLD
    ca.border = BORDER
    cb.border = BORDER
    ca.alignment = WRAP
    cb.alignment = WRAP
ws2.row_dimensions[1].height = 20

# ── SAVE ──────────────────────────────────────────────────────────────────────
XLSX = "/home/user/job-hunter/vancouver_businesses_only.xlsx"
CSV  = "/home/user/job-hunter/vancouver_businesses_only.csv"

wb.save(XLSX)
print(f"Saved XLSX: {XLSX}")

with open(CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([c.replace("\n", " ") for c in COLUMNS])
    for biz in businesses:
        writer.writerow(biz)
print(f"Saved CSV:  {CSV}")
print(f"Total businesses: {len(businesses)}")
