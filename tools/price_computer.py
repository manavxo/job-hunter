"""
Estimate a fair resale price for a used computer by scraping live listings.

Uses scrapegraph-ai (https://github.com/ScrapeGraphAI/Scrapegraph-ai) with a
DeepSeek LLM (OpenAI-compatible) to fetch one or more marketplace pages, extract
the comparable listings, and print a price range plus a fair-value estimate.

NOTE ON NETWORKING:
    This needs outbound access to BOTH the listing site (e.g. ebay.com) AND the
    DeepSeek API (api.deepseek.com). It will NOT work inside the restricted
    Claude Code cloud sandbox, whose proxy blocks both. Run it on your own
    machine, where there is no proxy.

Setup:
    pip install "scrapegraphai[burr]"
    playwright install chromium
    export DEEPSEEK_API_KEY=sk-...        # your DeepSeek key

Usage:
    # Default: scrape an eBay search for your build
    python tools/price_computer.py

    # Custom listing URL + describe the machine
    python tools/price_computer.py \
        --url "https://www.ebay.com/sch/i.html?_nkw=ryzen+7+3700x+gtx+1660+ti+32gb" \
        --specs "Ryzen 7 3700X, GTX 1660 Ti 6GB, 32GB DDR4, 500GB Samsung EVO SSD, Windows 11"

Input:  a marketplace search/listing URL + a free-text spec string
Output: JSON of comparable listings + a printed fair-value range
"""

import argparse
import json
import os
import sys

DEFAULT_SPECS = (
    "AMD Ryzen 7 3700X, ASUS TUF GTX 1660 Ti 6GB, 32GB DDR4, "
    "500GB Samsung EVO SSD, Thermaltake case, Windows 11"
)
DEFAULT_URL = (
    "https://www.ebay.com/sch/i.html?_nkw=ryzen+7+3700x+gtx+1660+ti+32gb&_sop=12"
)


def build_config(api_key: str) -> dict:
    """scrapegraph-ai config pointed at DeepSeek's OpenAI-compatible endpoint."""
    return {
        "llm": {
            "api_key": api_key,
            "model": "openai/deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "temperature": 0,
        },
        "verbose": True,
        "headless": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="marketplace search/listing URL")
    parser.add_argument("--specs", default=DEFAULT_SPECS, help="description of the machine")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: set DEEPSEEK_API_KEY in your environment first.", file=sys.stderr)
        print("  export DEEPSEEK_API_KEY=sk-...", file=sys.stderr)
        return 1

    try:
        from scrapegraphai.graphs import SmartScraperGraph
    except ImportError:
        print('ERROR: scrapegraph-ai not installed. Run: pip install "scrapegraphai[burr]"',
              file=sys.stderr)
        return 1

    prompt = (
        "Extract every used computer/PC listing on this page that is comparable to a "
        f"machine with these specs: {args.specs}. For each listing return a JSON object "
        "with fields: title, price (number, USD), currency, and condition. Ignore "
        "listings for individual parts only — prefer complete systems. Return a JSON "
        'list under the key "listings".'
    )

    print(f"Scraping: {args.url}\nFor specs: {args.specs}\n")
    scraper = SmartScraperGraph(prompt=prompt, source=args.url, config=build_config(api_key))
    result = scraper.run()

    listings = result.get("listings", []) if isinstance(result, dict) else []
    print(json.dumps(result, indent=2))

    prices = []
    for item in listings:
        try:
            prices.append(float(str(item.get("price")).replace(",", "").replace("$", "")))
        except (TypeError, ValueError):
            continue

    if prices:
        prices.sort()
        low, high = prices[0], prices[-1]
        mid = prices[len(prices) // 2]
        print("\n=== PRICE SUMMARY (USD) ===")
        print(f"  comparable listings found: {len(prices)}")
        print(f"  range:        ${low:,.0f} - ${high:,.0f}")
        print(f"  median:       ${mid:,.0f}")
        print(f"  fair value:   ~${mid:,.0f}  (list ~10-15% higher to leave negotiating room)")
    else:
        print("\nNo prices parsed — try a different URL or broaden --specs.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
