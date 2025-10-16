#!/usr/bin/env python3
"""
Generate WPLS_Pairs_PulseXv2.json

- Loads the PulseX v2 LP JSON (default: /mnt/fiveh/DATA/pulsex_v2_lps.json)
- Finds all tokens paired with the WPLS address
- Filters the original LP list to only LPs where token0 or token1 is in that paired-token set
- Writes the result to WPLS_Pairs_PulseXv2.json in the current directory

Run:
    python3 generate_wpls_pairs.py

"""
import json
import os
import sys

DATA_FILE = os.environ.get("PULSEX_V2_FILE", "/mnt/fiveh/DATA/pulsex_v2_lps.json")
TARGET = "0xA1077a294dDE1B09bB078844df40758a5D0f9a27".lower()
OUT_FILE = "WPLS_Pairs_PulseXv2.json"


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if not os.path.exists(DATA_FILE):
        print(f"Input file not found: {DATA_FILE}")
        sys.exit(1)

    data = load_data(DATA_FILE)
    print(f"Loaded {len(data)} LP entries from {DATA_FILE}")

    # collect tokens paired with TARGET
    partners = set()
    for item in data:
        t0 = (item.get("token0") or "").lower()
        t1 = (item.get("token1") or "").lower()
        if t0 == TARGET and t1:
            partners.add(t1)
        if t1 == TARGET and t0:
            partners.add(t0)

    print(f"Found {len(partners)} unique tokens paired with {TARGET}")

    # filter original list to keep only LPs where token0 or token1 in partners
    filtered = []
    for item in data:
        t0 = (item.get("token0") or "").lower()
        t1 = (item.get("token1") or "").lower()
        if t0 in partners or t1 in partners:
            filtered.append(item)

    print(f"Filtered to {len(filtered)} LPs that include one of those tokens")

    # save
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2)

    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
