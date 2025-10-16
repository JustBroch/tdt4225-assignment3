#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed EDA for TDT4225 Assignment 3.

You can:
- import run_detailed_eda(DATA_DIR, use_ratings_small) from EDA.py, OR
- run this file directly (it will use DATA_DIR below).

All standard library. Streams CSVs (no pandas).
"""

from pathlib import Path
import csv
import ast
from collections import Counter, defaultdict
from datetime import datetime
import time

# --------- CONFIG WHEN RUN DIRECTLY ----------
DATA_DIR = Path("/Users/saraostdahl/development/TDT4225/tdt4225-assignment3/data/raw")
USE_RATINGS_SMALL = False  # set True for faster runs

# --------------- HELPERS ----------------
def as_str(x):
    return "" if x is None else str(x)

def to_float_safe(x):
    try:
        s = as_str(x).strip()
        return float(s) if s else None
    except Exception:
        return None

def parse_list(cell):
    """Parse JSON-ish arrays (single quotes, null/None/False). Always returns list."""
    try:
        s = as_str(cell).strip()
        if not s or s.lower() in {"null", "none", "false"}:
            return []
        v = ast.literal_eval(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []

def text_hist_from_counts(counts_dict, title, max_bar=40, min_share=0.01):
    """Small horizontal bar chart in text from a {label: count} dict."""
    total = sum(counts_dict.values())
    print(f"\n{title} (top bins, {total:,} values):") if total else print(f"\n{title}: (no data)")
    if total == 0:
        return
    items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    for label, c in items:
        share = c / total
        if share < min_share:
            continue
        n = max(1, int(share * max_bar))
        print(f"  {str(label):15} {c:>10,}  {'█' * n}  ({share:.1%})")

# --------------- MOVIES ----------------
def detailed_movies_metadata(path: Path):
    decade_counts = Counter()
    genre_counts = Counter()
    lang_counts = Counter()

    runtime_bins = Counter()
    budget_bins  = Counter()
    revenue_bins = Counter()
    vote_avg_bins = Counter()
    vote_count_bins = Counter()

    miss_release = 0
    bad_dates = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            # release_date → decade
            rd = as_str(row.get("release_date")).strip()
            if not rd:
                miss_release += 1
            else:
                try:
                    dt = datetime.strptime(rd, "%Y-%m-%d")
                    decade_counts[(dt.year // 10) * 10] += 1
                except Exception:
                    bad_dates += 1

            # language
            lang = as_str(row.get("original_language")).strip()
            if lang:
                lang_counts[lang] += 1

            # genres
            for g in parse_list(row.get("genres", "")):
                name = as_str(g.get("name")).strip()
                if name:
                    genre_counts[name] += 1

            # runtime bins
            rt = to_float_safe(row.get("runtime"))
            if rt is None: runtime_bins["missing"] += 1
            elif rt == 0: runtime_bins["zero"] += 1
            elif rt < 60: runtime_bins["<60"] += 1
            elif rt < 90: runtime_bins["60-89"] += 1
            elif rt < 120: runtime_bins["90-119"] += 1
            elif rt < 150: runtime_bins["120-149"] += 1
            else: runtime_bins["150+"] += 1

            # money bins helper
            def money_bin(field, bins):
                x = to_float_safe(row.get(field))
                if x is None: bins["missing"] += 1
                elif x == 0: bins["0"] += 1
                elif x <= 1_000_000: bins["<=1e6"] += 1
                elif x <= 10_000_000: bins["1e6-1e7"] += 1
                elif x <= 100_000_000: bins["1e7-1e8"] += 1
                else: bins[">1e8"] += 1

            money_bin("budget", budget_bins)
            money_bin("revenue", revenue_bins)

            # vote_average (0.5 buckets)
            va = to_float_safe(row.get("vote_average"))
            if va is None: vote_avg_bins["missing"] += 1
            else: vote_avg_bins[f"{round(va * 2)/2:.1f}"] += 1

            # vote_count
            vc = to_float_safe(row.get("vote_count"))
            if vc is None: vote_count_bins["missing"] += 1
            elif vc == 0: vote_count_bins["0"] += 1
            elif vc <= 10: vote_count_bins["1-10"] += 1
            elif vc <= 50: vote_count_bins["11-50"] += 1
            elif vc <= 200: vote_count_bins["51-200"] += 1
            else: vote_count_bins[">200"] += 1

    print("\n=== Detailed EDA: movies_metadata.csv ===")
    if miss_release or bad_dates:
        print(f"release_date missing: {miss_release:,}  |  bad format: {bad_dates:,}")
    text_hist_from_counts(decade_counts, "Movies by decade", min_share=0.01)
    text_hist_from_counts(lang_counts, "Original language (top)", min_share=0.02)
    text_hist_from_counts(genre_counts, "Genres (top)", min_share=0.02)
    text_hist_from_counts(runtime_bins, "Runtime minutes (binned)")
    text_hist_from_counts(budget_bins, "Budget USD (binned)")
    text_hist_from_counts(revenue_bins, "Revenue USD (binned)")
    text_hist_from_counts(vote_avg_bins, "Vote average (0–10, 0.5 steps)")
    text_hist_from_counts(vote_count_bins, "Vote count (binned)")

# --------------- CREDITS ---------------
def detailed_credits(path: Path):
    cast_sizes, crew_sizes = [], []
    has_director = 0
    director_counts = Counter()
    n = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            cast = parse_list(row.get("cast", ""))
            crew = parse_list(row.get("crew", ""))
            cast_sizes.append(len(cast))
            crew_sizes.append(len(crew))
            found_dir = False
            for m in crew:
                if as_str(m.get("job")).strip() == "Director":
                    found_dir = True
                    name = as_str(m.get("name")).strip()
                    if name:
                        director_counts[name] += 1
            if found_dir:
                has_director += 1

    print("\n=== Detailed EDA: credits.csv ===")
    print(f"Movies with at least one Director entry: {has_director:,} / {n:,} "
          f"({has_director / max(n,1):.1%})")

    def size_bins(arr):
        b = Counter()
        for x in arr:
            if x == 0: b["0"] += 1
            elif x <= 5: b["1-5"] += 1
            elif x <= 20: b["6-20"] += 1
            elif x <= 50: b["21-50"] += 1
            else: b["51+"] += 1
        return b

    text_hist_from_counts(size_bins(cast_sizes), "Cast size (per movie)")
    text_hist_from_counts(size_bins(crew_sizes), "Crew size (per movie)")
    text_hist_from_counts(director_counts, "Most common directors (top)", min_share=0.003)

# -------------- KEYWORDS ---------------
def detailed_keywords(path: Path):
    sizes = []
    kw_counts = Counter()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            kws = parse_list(row.get("keywords", ""))
            sizes.append(len(kws))
            for k in kws:
                name = as_str(k.get("name")).strip()
                if name:
                    kw_counts[name] += 1

    print("\n=== Detailed EDA: keywords.csv ===")

    def size_bins(arr):
        b = Counter()
        for x in arr:
            if x == 0: b["0"] += 1
            elif x <= 3: b["1-3"] += 1
            elif x <= 10: b["4-10"] += 1
            else: b["11+"] += 1
        return b

    text_hist_from_counts(size_bins(sizes), "Keywords per movie")
    text_hist_from_counts(kw_counts, "Top keywords", min_share=0.003)

# -------------- RATINGS ----------------
def detailed_ratings(path: Path):
    val_counts = Counter()
    per_user = Counter()
    t_min, t_max = None, None

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rv = to_float_safe(row.get("rating"))
            if rv is not None:
                val_counts[f"{round(rv * 2)/2:.1f}"] += 1
            uid = as_str(row.get("userId")).strip()
            if uid:
                per_user[uid] += 1
            ts = to_float_safe(row.get("timestamp"))
            if ts is not None:
                ts = int(ts)
                t_min = ts if t_min is None else min(t_min, ts)
                t_max = ts if t_max is None else max(t_max, ts)

    print("\n=== Detailed EDA: ratings.csv ===")
    text_hist_from_counts(val_counts, "Rating values (0.5 steps)", min_share=0.01)

    def user_bins(cnts: Counter):
        b = Counter()
        for _, x in cnts.items():
            if x <= 10: b["<=10"] += 1
            elif x <= 50: b["11-50"] += 1
            elif x <= 200: b["51-200"] += 1
            else: b[">200"] += 1
        return b

    text_hist_from_counts(user_bins(per_user), "Ratings per user")

    if t_min is not None and t_max is not None:
        print(f"Time span: {time.strftime('%Y-%m-%d', time.gmtime(t_min))} → "
              f"{time.strftime('%Y-%m-%d', time.gmtime(t_max))}")

# ------------- PUBLIC API --------------
def run_detailed_eda(base_dir: Path, use_ratings_small: bool):
    """Call from EDA.py to run the detailed analysis."""
    p = base_dir / "movies_metadata.csv"
    if p.exists(): detailed_movies_metadata(p)
    p = base_dir / "credits.csv"
    if p.exists(): detailed_credits(p)
    p = base_dir / "keywords.csv"
    if p.exists(): detailed_keywords(p)
    p = base_dir / ("ratings_small.csv" if use_ratings_small else "ratings.csv")
    if p.exists(): detailed_ratings(p)

# ------------- CLI MODE ----------------
if __name__ == "__main__":
    run_detailed_eda(DATA_DIR, USE_RATINGS_SMALL)
