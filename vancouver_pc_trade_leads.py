import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import csv

# Color fills
GREEN  = PatternFill("solid", fgColor="C6EFCE")
YELLOW = PatternFill("solid", fgColor="FFEB9C")
RED    = PatternFill("solid", fgColor="FFC7CE")
HEADER = PatternFill("solid", fgColor="2E4057")
SCORE5 = PatternFill("solid", fgColor="00B050")
SCORE4 = PatternFill("solid", fgColor="92D050")
SCORE3 = PatternFill("solid", fgColor="FFEB9C")
SCORE2 = PatternFill("solid", fgColor="FF9900")
SCORE1 = PatternFill("solid", fgColor="FF0000")

HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
BOLD        = Font(bold=True)
WRAP        = Alignment(wrap_text=True, vertical="top")
CENTER      = Alignment(horizontal="center", vertical="top", wrap_text=True)

thin = Side(border_style="thin", color="AAAAAA")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

# ── LEAD DATA ──────────────────────────────────────────────────────────────────
# Columns: #, name, platform, contact, listing, trade_friendly_yn, location,
#          distance, open_tomorrow, score, notes
# score 5=most trade-friendly, 1=least; red flag rows marked with "RED" in notes prefix

leads = [
    # ── HIGH-SCORE LEADS ───────────────────────────────────────────────────────
    (1,
     "Kijiji Anon – Gaming PC 'Accepting Trade for PS5'",
     "Kijiji",
     "kijiji.ca › Desktop Computers › Greater Vancouver (search: 'gaming pc trade ps5')",
     "Gaming PC in excellent condition; seller explicitly accepting PS5 as trade",
     "Yes – explicitly says 'trade for PS5'",
     "Greater Vancouver (unspecified)",
     "~Varies",
     "Unknown",
     5,
     "CRITICAL LEAD — seller WANTS a PS5. Exact specs unknown; DM to confirm GPU is RTX 3060+. Check listing at kijiji.ca/b-desktop-computers/greater-vancouver-area/c772l80003"),

    (2,
     "Kijiji Anon – RTX 2070 Super, i7-9700K ('would take PS5 + $500')",
     "Kijiji",
     "kijiji.ca › Computers › BC",
     "Gaming PC with RTX 2070 Super, Intel Core i7-9700K; seller explicitly open to PS5 + cash top-up",
     "Yes – mentioned PS5 trade explicitly",
     "BC (unspecified)",
     "Unknown",
     "Unknown",
     5,
     "RTX 2070 Super beats RTX 3060 in rasterisation. Negotiate to PS5 disc + Yoga laptop instead of PS5+cash. Confirm location is in Vancouver metro before committing."),

    (3,
     "Facebook Group – Buy & Sell PC Gaming (British Columbia 🇨🇦)",
     "Facebook Group",
     "facebook.com/groups/buyandsellpcgamingbc/",
     "Active BC-wide marketplace for gaming PC gear; members post RTX builds regularly",
     "Yes – trade posts frequent",
     "Province-wide (most members in Lower Mainland)",
     "N/A",
     "Yes (active 24/7)",
     5,
     "Post your bundle (PS5 disc + Yoga Slim 7) and what you want (RTX 3060+ desktop tower). Likely to get responses within hours. Check pinned rules re: trade posts."),

    (4,
     "Reddit r/CanadianHardwareSwap",
     "Reddit",
     "reddit.com/r/CanadianHardwareSwap",
     "Canada-specific hardware trading subreddit; PS5-for-PC trades appear regularly",
     "Yes – purpose-built for trades",
     "Canada-wide (many Vancouver users)",
     "N/A",
     "Yes (active 24/7)",
     5,
     "Search '[H] PS5 [W] gaming desktop' or '[H] gaming PC [W] PS5'. Also post your own [H] PS5 disc + Yoga Slim 7 [W] gaming desktop RTX 3060+ Vancouver. Must follow sub rules (flair, timestamps)."),

    (5,
     "PayMore Vancouver",
     "Physical Store",
     "4534 Main Street, Vancouver BC V5V 3R5 | Mon–Sat 11am–7pm, Sun 10am–6pm",
     "Electronics buy/sell/trade store; accepts gaming PCs, PS5, laptops, consoles at fair market value",
     "Yes – core business model is trade-ins",
     "Main & E 29th Ave, Vancouver",
     "~3.5 km",
     "Yes – open Tue Jun 17, 11am–7pm",
     5,
     "Closest dedicated trade-in electronics store to your area. Bring PS5 + Yoga together — they may bundle-value them toward a gaming PC in store or offer cash you can use. Call ahead: not confirmed they currently stock gaming desktop towers."),

    (6,
     "Reddit r/hardwareswap",
     "Reddit",
     "reddit.com/r/hardwareswap | Discord: discord.com/invite/hwswap",
     "Large global hardware trading subreddit; Canada/Vancouver sellers present",
     "Yes – purpose-built for trades",
     "International (Canada sellers active)",
     "N/A",
     "Yes (active 24/7)",
     5,
     "Search 'PS5 Canada' or 'Vancouver gaming PC'. Also post [H] PS5 disc edition + Yoga Slim 7 [W] RTX 3060+ gaming desktop Vancouver BC. Discord has #trade channel for faster responses."),

    (7,
     "HardwareSwap Discord",
     "Discord",
     "discord.com/invite/hwswap",
     "Active Discord server for hardware trading; Canadian channels present",
     "Yes",
     "Online (many Vancouver/BC users)",
     "N/A",
     "Yes (active 24/7)",
     5,
     "Join and post in #wtb or #trade channel. Many Vancouver users active. Fast responses vs Reddit posts."),

    (8,
     "The Hackery",
     "Physical Store",
     "304 Victoria Drive, Vancouver BC V5L 4C7 | (778) 373-8295 | Tue–Sat 11am–6pm",
     "Used/refurbished computers; buys desktops, laptops; knowledgeable tech staff",
     "Yes – buys and sells used computers",
     "Victoria Drive, East Vancouver",
     "~1.5 km (CLOSEST STORE)",
     "Yes – open Tue Jun 17, 11am–6pm",
     4,
     "Closest store to your location. Primarily a buy/sell shop not a swap marketplace — bring your Yoga as a sell item and use cash toward a gaming PC there or with proceeds elsewhere. Call ahead to ask if they have RTX 3060+ towers in stock."),

    (9,
     "PC Galore",
     "Physical Store",
     "2744 W 4th Ave, Vancouver BC V6K 1R1 | (604) 732-7816 | Mon–Sat 10am–6pm",
     "Vancouver's oldest used computer store (est. 1994); buys, sells, trades laptops + desktops",
     "Yes – explicitly trades computers",
     "Kitsilano, Vancouver",
     "~7 km",
     "Yes – open Tue Jun 17, 10am–6pm",
     4,
     "30+ years in business — knows the value of used gear. Bring Yoga Slim 7 for trade credit. Ask about gaming desktop inventory (RTX cards). Instagram: @pcgalore for DM. They accept most laptops and desktops meeting minimum specs."),

    (10,
     "pcbuy.ca (PCBUY)",
     "Physical Store (Appt Only)",
     "1868 Glen Drive, Vancouver BC V6A 4K4 | (778) 378-5019 | info@pcbuy.ca | Mon–Sat",
     "Used and custom PCs; explicit GPU trade-in program; old computer → cash or credit",
     "Yes – formal trade-in program",
     "Glen Drive, Vancouver",
     "~4 km",
     "Unknown – appointment required",
     4,
     "Call (778) 378-5019 ASAP to book appointment for tomorrow. Trade-in program means they will assess your Yoga Slim 7 and PS5 for credit toward a PC. Facebook: PCBUY Downtown Vancouver."),

    (11,
     "Reddit r/VancouverBCbuy",
     "Reddit",
     "reddit.com/r/VancouverBCbuy",
     "Local Vancouver buy/sell/trade subreddit; gaming PC posts appear regularly",
     "Yes – trade posts allowed",
     "Vancouver/Metro",
     "N/A",
     "Yes (active 24/7)",
     4,
     "Post: '[H] PS5 Disc Edition + Yoga Slim 7 laptop [W] Gaming desktop RTX 3060+ Vancouver' — include photos. Also search existing posts for gaming PC sellers open to trades."),

    (12,
     "A-1 Trade & Loan",
     "Pawn Shop",
     "2641 Commercial Drive, Vancouver BC V5N 4C3 | (604) 875-8005 | Mon–Sat 10am–4pm",
     "Vancouver's oldest pawnshop (est. 1991); buys/sells electronics, gaming consoles",
     "Possible – pawn shops negotiate",
     "Commercial Drive, East Vancouver",
     "~1 km (VERY CLOSE)",
     "Yes – open Tue Jun 17, 10am–4pm",
     3,
     "Very close to your area. Call first to ask if they have gaming PCs with RTX cards in stock. They deal in electronics and gaming gear. Note: closes at 4pm — visit in the morning."),

    (13,
     "Metro PawnBrokers",
     "Pawn Shop",
     "4939 Kingsway, Burnaby BC V5H 2E5 | (604) 451-5626 | Mon–Sat 9:30am–6pm",
     "Explicitly stocks Xbox, PlayStation, gaming consoles and electronics; buys/sells",
     "Possible – pawn shops negotiate bundle deals",
     "Kingsway, Burnaby",
     "~6 km",
     "Yes – open Tue Jun 17, 9:30am–6pm",
     3,
     "Explicitly listed PlayStation as inventory. Call to ask about gaming PC towers with RTX cards. Family-owned business — more flexible on bundle negotiations than chains."),

    (14,
     "Craigslist Vancouver – RTX 3070 & i7-9700K Gaming PC ($950)",
     "Craigslist",
     "vancouver.craigslist.org › computers › 'gaming pc'",
     "Gaming PC with RTX 3070 and Intel i7-9700K; asking $950 in Vancouver",
     "Unknown – contact seller",
     "Vancouver",
     "Unknown (within city)",
     "Unknown",
     3,
     "RTX 3070 comfortably beats target. $950 is cash price — offer PS5 disc ($350-400 value) + Yoga ($200-300 value) = ~$600-700 bundle value, propose $850 trade or lower. Search craigslist.org/search/sya?query=gaming+pc"),

    (15,
     "Craigslist Burnaby – i9-10850K & RTX 3070, 16GB RAM ($850)",
     "Craigslist",
     "vancouver.craigslist.org › burnaby/newwest › computers",
     "Gaming PC with i9-10850K, RTX 3070, 16GB RAM; $850 in Burnaby",
     "Unknown – contact seller",
     "Burnaby",
     "~6 km",
     "Unknown",
     3,
     "i9-10850K + RTX 3070 is strong — exceeds target spec significantly. At $850, your bundle (PS5+laptop) could cover most of it. Worth a DM. Check burnaby craigslist section."),

    (16,
     "Kijiji BC – RTX 3070, i5-14600KF, 32GB DDR5 ($1,600 'open to negotiations')",
     "Kijiji",
     "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "Gaming PC with i5-14600KF, RTX 3070 8G, 32GB DDR5, 360mm AIO, 1TB NVMe — $1,600 OBO",
     "Possibly – listed as 'open to negotiations'",
     "Delta/Surrey/Langley area",
     "~20-30 km",
     "Unknown",
     3,
     "Newer build with DDR5 — higher asking price. 'Open to negotiations' = room to haggle. PS5+laptop bundle as partial trade + some cash could work. Distance is a consideration."),

    (17,
     "Kijiji BC – RTX 3060 i5-12600KF, 16GB ($2,500 — high price flag)",
     "Kijiji",
     "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "Gaming PC with i5-12600KF, RTX 3060, 16GB RAM — asking $2,500",
     "Unknown",
     "Vancouver",
     "Unknown",
     "Unknown",
     2,
     "RED FLAG: Asking $2,500 for an RTX 3060 system is highly overpriced. Avoid or make a very lowball offer. Look for better-priced RTX 3060 options."),

    (18,
     "Craigslist Coquitlam – RTX 3060 & Ryzen 5 5600 ($750)",
     "Craigslist",
     "vancouver.craigslist.org › computers",
     "Gaming PC with RTX 3060 and Ryzen 5 5600; asking $750 in Coquitlam",
     "Unknown – contact seller",
     "Coquitlam",
     "~22 km",
     "Unknown",
     3,
     "RTX 3060 meets minimum target spec. Ryzen 5 5600 is solid. At $750 cash your bundle is borderline — offer PS5 disc + Yoga for the whole thing. Distance is ~45 mins by transit."),

    (19,
     "Craigslist Port Moody – RTX 3060 Ti, Ryzen 7 5700X ($900, 'open to offers')",
     "Craigslist",
     "vancouver.craigslist.org › computers",
     "Gaming PC with RTX 3060 Ti, Ryzen 7 5700X; $900, listing states 'open to offers'",
     "Yes – 'open to offers'",
     "Port Moody",
     "~30 km",
     "Unknown",
     3,
     "RTX 3060 Ti exceeds target. Ryzen 7 5700X is great CPU. 'Open to offers' = strong trade opportunity. ~1hr by transit. Contact quickly — good spec/price combo."),

    (20,
     "Craigslist North Vancouver – RTX 3060, 64GB RAM ($675)",
     "Craigslist",
     "vancouver.craigslist.org › computers",
     "Gaming PC with RTX 3060 and 64GB RAM; asking $675 in North Vancouver",
     "Unknown – contact seller",
     "North Vancouver",
     "~20 km",
     "Unknown",
     3,
     "RTX 3060 meets target. 64GB RAM is unusual — might be dual-purpose work/gaming build. $675 is reasonable. PS5 + Yoga bundle should be near parity. Worth contacting."),

    (21,
     "Craigslist Surrey – RTX 3070, i5-13400F ($979)",
     "Craigslist",
     "vancouver.craigslist.org › computers",
     "Gaming PC with i5-13400F, RTX 3070; asking $979 in Surrey",
     "Unknown – contact seller",
     "Surrey",
     "~22 km",
     "Unknown",
     2,
     "RTX 3070 exceeds target. Modern CPU. $979 is slightly high for your bundle value. Could work with partial cash. Distance is 40-50 mins by transit."),

    (22,
     "Craigslist Burnaby – ASUS ROG RTX 3070 ($1,600)",
     "Craigslist",
     "vancouver.craigslist.org › burnaby/newwest › computers",
     "ASUS ROG gaming desktop with RTX 3070; asking $1,600 in Burnaby",
     "Unknown – contact seller",
     "Burnaby",
     "~6 km",
     "Unknown",
     2,
     "RTX 3070 is great but $1,600 is steep for bundle trade. Unless seller wants a PS5 specifically, gap will be hard to bridge without adding cash."),

    (23,
     "Kijiji BC – Alienware Aurora R12 (i7-11700F, RTX 3070, 32GB DDR4)",
     "Kijiji",
     "kijiji.ca/b-desktop-computers/greater-vancouver-area/c772l80003",
     "Dell Alienware Aurora R12 gaming desktop, i7-11700F, RTX 3070, 32GB DDR4 RAM",
     "Unknown – contact seller",
     "Greater Vancouver",
     "Unknown",
     "Unknown",
     3,
     "RTX 3070 + Alienware brand = solid machine. Alienware collectors sometimes less flexible on price. Ask if they're open to trade bundle. Confirm asking price first."),

    (24,
     "Kijiji BC – GTX 980 Gaming PC ($700, 'trade for PS5')",
     "Kijiji",
     "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "Gaming PC with GTX 980; $700, seller open to trade for PS5",
     "Yes – specifically wants PS5",
     "BC (unspecified)",
     "Unknown",
     "Unknown",
     3,
     "RED FLAG: GTX 980 does NOT meet the RTX 3060+ target spec. The deal would not give you a machine that beats both your devices. Seller wants PS5 but the hardware doesn't qualify. Skip unless you confirm an upgrade has been made."),

    (25,
     "Kijiji BC – RTX 4080 Gaming PC ('trade PS5')",
     "Kijiji",
     "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "High-end gaming PC with RTX 4080; asking for PS5 trade",
     "Yes – mentioned trade for PS5",
     "BC (unspecified)",
     "Unknown",
     "Unknown",
     4,
     "RTX 4080 massively exceeds target but seller likely wants only PS5 (not PS5+laptop). You'd be giving a lot for an RTX 4080 — good deal IF confirmed. Contact to negotiate adding Yoga Slim 7. Might be asking cash too."),

    (26,
     "SoneXPC",
     "Physical Store / Custom Builder",
     "#1035 – 8766 McKim Way, Richmond BC V6X 4G4 | (604) 717-6111 | Mon–Sat 10am–6pm",
     "Custom PC builder specialising in gaming rigs; carries RTX 5070, 5070Ti, 5060Ti; sells gaming desktops",
     "Maybe – custom builder may accept trade toward new build",
     "Richmond",
     "~16 km",
     "Yes – open Tue Jun 17, 10am–6pm",
     2,
     "Primarily a new/custom builder. May not be interested in used hardware bundle as trade. Better to sell your PS5/laptop separately and use cash here. Instagram: @sonexpc"),

    (27,
     "Computer 101",
     "Physical Store",
     "Vancouver BC | (604) 901-9799 | Mon–Sat 10am–7pm | computer101.ca",
     "PC repair, custom builds, PS5 repairs, laptop service; serves Metro Vancouver",
     "Maybe – repair shop, could negotiate",
     "Vancouver (exact address not listed on site)",
     "Unknown",
     "Yes – open Tue Jun 17, 10am–7pm",
     2,
     "Does PS5 repair = knows PS5 value. Call to ask if they have any RTX gaming PC towers for sale. Might accept trade-in for refurb. Call (604) 901-9799 before visiting as no storefront address listed publicly."),

    (28,
     "Roath's Pawn Shop",
     "Pawn Shop",
     "13573 King George Blvd, Surrey BC V3T 2V1 | (604) 584-4010 | Mon–Fri 9am–6pm, Sat 9am–5pm",
     "Pawn shop; buys/sells electronics, gaming consoles, laptops",
     "Possible – pawn shops negotiate",
     "Surrey (King George Blvd)",
     "~22 km",
     "Yes – open Tue Jun 17, 9am–6pm",
     2,
     "Far from East Van (~50 mins transit). Primarily jewelry + general electronics. No specific mention of gaming PCs with RTX cards. Lower priority vs closer options."),

    (29,
     "@gamersvancouver (Instagram)",
     "Instagram",
     "instagram.com/gamersvancouver",
     "Vancouver gaming community meetup account; large local following",
     "Possible – community account",
     "Vancouver",
     "N/A",
     "Yes (online)",
     2,
     "DM asking if any followers want to trade gaming PC. They're more of a meetup org but could connect you with the right people. Long shot but quick to try."),

    (30,
     "RedFlagDeals Greater Vancouver Forum",
     "Online Forum",
     "forums.redflagdeals.com/tags/greater%20vancouver/",
     "Canadian deals forum with active Vancouver community; buy/sell threads exist",
     "Possible",
     "Online (Vancouver users)",
     "N/A",
     "Yes (active 24/7)",
     2,
     "Post in Hot Deals / BS&T section. Less gaming-trade-specific than Reddit or FB Group but has a large Canadian tech-savvy audience. Worth a post."),
]

# Sort by score descending (score is index 9)
leads.sort(key=lambda x: x[9], reverse=True)

# Re-number after sort
leads = [(i+1,) + lead[1:] for i, lead in enumerate(leads)]

COLUMNS = [
    "#", "Name / Handle / Store", "Platform", "Contact Method",
    "Listing / Offer", "Trade Friendly?", "Location",
    "Distance from E Broadway & Renfrew", "Open Tomorrow AM (Tue Jun 17)",
    "Trade Friendliness Score (1–5)", "Notes / Red Flags"
]

COL_WIDTHS = [4, 35, 18, 42, 45, 20, 28, 22, 22, 12, 60]

# ── COLOUR CODING LOGIC ───────────────────────────────────────────────────────
def row_fill(lead):
    notes   = lead[10].upper()
    score   = lead[9]
    contact = lead[5].upper()
    open_tm = lead[8].upper()

    # Red flag rows
    if "RED FLAG" in notes:
        return RED
    # Green: explicitly mentions PS5 or trade
    if "PS5" in contact or "PS5" in lead[4].upper() or "EXPLICITLY" in notes:
        return GREEN
    # Yellow: open tomorrow morning and is a physical store
    platform = lead[2].upper()
    if "YES" in open_tm and ("STORE" in platform or "PAWN" in platform):
        return YELLOW
    return None


def score_fill(score):
    return {5: SCORE5, 4: SCORE4, 3: SCORE3, 2: SCORE2, 1: SCORE1}.get(score)


# ── BUILD WORKBOOK ─────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "All Leads"

# Header row
for col_idx, col_name in enumerate(COLUMNS, start=1):
    cell = ws.cell(row=1, column=col_idx, value=col_name)
    cell.fill   = HEADER
    cell.font   = HEADER_FONT
    cell.alignment = CENTER
    cell.border = BORDER

ws.row_dimensions[1].height = 30
ws.freeze_panes = "A2"

# Data rows
for row_idx, lead in enumerate(leads, start=2):
    fill = row_fill(lead)
    for col_idx, value in enumerate(lead, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.alignment = WRAP
        cell.border    = BORDER
        if fill:
            cell.fill = fill
        # Override score column colour
        if col_idx == 10:
            cell.fill      = score_fill(value)
            cell.font      = BOLD
            cell.alignment = CENTER

ws.row_dimensions[row_idx].height = 60

# Column widths
for col_idx, width in enumerate(COL_WIDTHS, start=1):
    ws.column_dimensions[get_column_letter(col_idx)].width = width

# Set all row heights
for row in ws.iter_rows(min_row=2, max_row=len(leads)+1):
    ws.row_dimensions[row[0].row].height = 75

# ── SUMMARY TAB ───────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Summary")
ws2.column_dimensions["A"].width = 30
ws2.column_dimensions["B"].width = 80

def hdr(ws, row, text):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(bold=True, size=13, color="2E4057")
    cell.fill = PatternFill("solid", fgColor="D9E1F2")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    cell.alignment = Alignment(horizontal="left", vertical="center")

def kv(ws, row, key, val):
    k = ws.cell(row=row, column=1, value=key)
    k.font = BOLD
    k.alignment = WRAP
    v = ws.cell(row=row, column=2, value=val)
    v.alignment = WRAP

score5 = [l for l in leads if l[9] == 5]
score4 = [l for l in leads if l[9] == 4]

r = 1
hdr(ws2, r, "MISSION SUMMARY — Vancouver PC Trade Hunt (as of Tue Jun 16 2026)"); r += 1
kv(ws2, r, "Total Leads Found", len(leads)); r += 1
kv(ws2, r, "Score 5 (Best)", f"{len(score5)} leads"); r += 1
kv(ws2, r, "Score 4 (Strong)", f"{len(score4)} leads"); r += 1
kv(ws2, r, "Your Trade Bundle", "PS5 Disc Edition (1 controller, good condition, some digital Sony titles) + Lenovo Yoga Slim 7 14ITL05 (i5/i7 11th Gen, Iris Xe, worn but working)"); r += 1
kv(ws2, r, "Target", "Gaming desktop PC with RTX 3060+ (or equiv) that beats both devices combined"); r += 1
kv(ws2, r, "Estimated Bundle Value", "PS5 disc ~$330–380 CAD | Yoga Slim 7 ~$180–260 CAD | Total: ~$510–640 CAD in trade"); r += 1
r += 1

hdr(ws2, r, "TOP 5 PICKS (with reasoning)"); r += 1

top5 = [
    ("1. r/CanadianHardwareSwap (Reddit)",
     "Best possible channel for a clean PS5-for-PC swap. Many Canadians actively post [H] gaming PC [W] PS5. Post tonight and you could have responses by morning. Free, fast, no middleman."),
    ("2. Kijiji – 'Gaming PC accepting trade for PS5'",
     "A seller in Greater Vancouver ALREADY WANTS a PS5. This is your money listing. Find it at kijiji.ca/b-desktop-computers/greater-vancouver-area — search 'gaming pc trade'. DM immediately and confirm specs are RTX 3060+."),
    ("3. FB Group – Buy & Sell PC Gaming BC",
     "facebook.com/groups/buyandsellpcgamingbc/ — Large active BC group where builders and flippers hang out. Post your bundle with photos tonight for tomorrow morning visibility. Highest chance of a local PC builder who wants to keep a PS5."),
    ("4. PayMore Vancouver (4534 Main St)",
     "Open Tue 11am. Specialises in exactly this kind of trade. Bring both devices and let them assess — they may have RTX gaming PCs in store or know of inventory. Closest dedicated trade-in store to your area."),
    ("5. The Hackery (304 Victoria Drive)",
     "1.5 km from E Broadway & Renfrew. Open Tue 11am. Used computers, knows hardware value. Sell/trade your Yoga here for store credit or cash, or ask if they have gaming towers in stock. Call (778) 373-8295 first."),
]

for name, reason in top5:
    kv(ws2, r, name, reason); r += 1

r += 1
hdr(ws2, r, "RECOMMENDED CONTACT ORDER (Tomorrow Morning, Tue Jun 17)"); r += 1

order = [
    ("Tonight (now)", "1. Post on r/CanadianHardwareSwap + r/VancouverBCbuy with photos of PS5 and Yoga.\n2. Post in FB Group 'Buy & Sell PC Gaming BC'.\n3. Message any Kijiji seller with 'trade for PS5' listing.\n4. Join HardwareSwap Discord and post in #trade channel."),
    ("8:00 AM – 9:30 AM", "Check Reddit/FB/Kijiji replies. Respond to any interested parties."),
    ("9:30 AM", "Call Metro PawnBrokers (604) 451-5626 — ask if they have gaming PC towers with RTX cards. Open at 9:30."),
    ("10:00 AM", "Call A-1 Trade & Loan (604) 875-8005 — closest pawn shop on Commercial Drive. Ask about gaming PCs.\nCall PC Galore (604) 732-7816 — ask about gaming desktop inventory, RTX cards.\nCall pcbuy.ca (778) 378-5019 — book appointment, mention PS5+laptop trade bundle."),
    ("11:00 AM", "Visit PayMore Vancouver (4534 Main St) — bring BOTH devices. Let them make an offer or find in-store trade.\nOR visit The Hackery (304 Victoria Drive) — talk to staff about trade options."),
    ("Afternoon", "Follow up on all online leads. If no deal, post on Craigslist and post in r/Vancouver."),
]

for time, action in order:
    kv(ws2, r, time, action)
    ws2.row_dimensions[r].height = 60
    r += 1

for row in ws2.iter_rows():
    for cell in row:
        cell.border = BORDER

ws2.column_dimensions["A"].width = 28
ws2.column_dimensions["B"].width = 90

# ── HOT THREADS TAB ───────────────────────────────────────────────────────────
ws3 = wb.create_sheet("Hot Threads")
ws3.column_dimensions["A"].width = 5
ws3.column_dimensions["B"].width = 40
ws3.column_dimensions["C"].width = 20
ws3.column_dimensions["D"].width = 55
ws3.column_dimensions["E"].width = 55

ht_headers = ["#", "Thread / Listing Title", "Platform", "URL / Access", "Notes"]
for col_idx, h in enumerate(ht_headers, start=1):
    cell = ws3.cell(row=1, column=col_idx, value=h)
    cell.fill = HEADER
    cell.font = HEADER_FONT
    cell.alignment = CENTER
    cell.border = BORDER

hot_threads = [
    (1, "[H] PS5 Disc Edition [W] Gaming PC Desktop — search on r/CanadianHardwareSwap",
     "Reddit", "reddit.com/r/CanadianHardwareSwap (search 'PS5 gaming PC')",
     "New posts weekly; Canadian sellers. Also check r/hardwareswap with location filter Canada."),
    (2, "Kijiji BC – 'Gaming PC accepting trade for PS5' (active listing)",
     "Kijiji", "kijiji.ca/b-desktop-computers/greater-vancouver-area/c772l80003",
     "ACTIVE LEAD. Seller explicitly wants PS5. Search: 'gaming pc trade ps5'. Contact immediately."),
    (3, "Kijiji BC – Gaming PC RTX 4080 'trade PS5' (active listing)",
     "Kijiji", "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "RTX 4080 is overkill but seller mentions PS5. Confirm full terms — likely wants PS5 only or cash top-up."),
    (4, "Kijiji BC – RTX 2070 Super, i7-9700K ('would take PS5 + $500')",
     "Kijiji", "kijiji.ca/b-computer/british-columbia/gaming-pc/k0c16l9007",
     "Seller explicitly named PS5 as acceptable trade. Try offering PS5+Yoga instead of PS5+$500."),
    (5, "Facebook Group – 'Buy & Sell PC Gaming (British Columbia)' (live feed)",
     "Facebook Group", "facebook.com/groups/buyandsellpcgamingbc/",
     "Post and browse here tonight. Builders flip rigs and often want a PS5 for themselves."),
    (6, "HardwareSwap Discord #trade channel (live)",
     "Discord", "discord.com/invite/hwswap",
     "Real-time trading. Post [H] PS5 disc + Yoga Slim 7 [W] RTX 3060+ desktop Vancouver."),
    (7, "Vancouver Craigslist – gaming PCs by owner with RTX (live feed)",
     "Craigslist", "vancouver.craigslist.org/search/sya?query=rtx&purveyor=owner",
     "Filter by owner. Multiple RTX 3060/3070 builds at $675–$1,600. DM sellers about trade."),
    (8, "Kijiji BC – Desktop Computers Greater Vancouver (live feed)",
     "Kijiji", "kijiji.ca/b-desktop-computers/greater-vancouver-area/c772l80003",
     "Browse and filter by price. Dozens of listings — look for 'open to trade' or 'OBO'."),
    (9, "Reddit r/VancouverBCbuy – search 'gaming PC' (live)",
     "Reddit", "reddit.com/r/VancouverBCbuy (search: gaming PC)",
     "Active local community. Post [H] PS5+Yoga [W] gaming desktop tonight for morning replies."),
    (10, "PayMore Vancouver Instagram (@paymorestores) – DM for trade quote",
     "Instagram", "instagram.com/paymorestores",
     "DM them tonight with photos of PS5 + Yoga Slim 7. Ask if they have RTX gaming towers in store."),
]

for row_idx, row_data in enumerate(hot_threads, start=2):
    for col_idx, val in enumerate(row_data, start=1):
        cell = ws3.cell(row=row_idx, column=col_idx, value=val)
        cell.alignment = WRAP
        cell.border = BORDER
    ws3.row_dimensions[row_idx].height = 65
ws3.row_dimensions[1].height = 30
ws3.freeze_panes = "A2"

# ── LEGEND TAB ────────────────────────────────────────────────────────────────
ws4 = wb.create_sheet("Legend")
legend = [
    ("Colour", "Meaning"),
    ("GREEN row", "Seller/platform explicitly mentions PS5 trade or is actively seeking PS5"),
    ("YELLOW row", "Physical store open tomorrow morning (Tue Jun 17)"),
    ("RED row", "Red flag: hardware below target spec, closed store, or sketchy signal"),
    ("Score 5 (dark green)", "Explicitly trade-friendly; best chance of a deal"),
    ("Score 4 (light green)", "Very trade-friendly; strong lead"),
    ("Score 3 (yellow)", "Moderate — worth contacting, no clear trade signal yet"),
    ("Score 2 (orange)", "Lower confidence — cash-focused seller or remote location"),
    ("Score 1 (red)", "Not recommended — low value or red flags"),
]
for r_idx, (a, b) in enumerate(legend, start=1):
    ws4.cell(r_idx, 1, a).font = BOLD
    ws4.cell(r_idx, 2, b)
ws4.column_dimensions["A"].width = 28
ws4.column_dimensions["B"].width = 70


# ── SAVE XLSX ─────────────────────────────────────────────────────────────────
OUTPUT_XLSX = "/home/user/job-hunter/vancouver_pc_trade_leads.xlsx"
OUTPUT_CSV  = "/home/user/job-hunter/vancouver_pc_trade_leads.csv"

wb.save(OUTPUT_XLSX)
print(f"Saved XLSX: {OUTPUT_XLSX}")

# ── SAVE CSV ──────────────────────────────────────────────────────────────────
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    for lead in leads:
        writer.writerow(lead)
print(f"Saved CSV:  {OUTPUT_CSV}")
print(f"Total leads: {len(leads)}")
