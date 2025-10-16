# save as: viz_entries.py
from pathlib import Path
import csv, ast
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"

FILES = [
    "movies_metadata.csv",
    "credits.csv",
    "keywords.csv",
    "ratings.csv",     # use ratings_small.csv for speed if you want
    "links.csv",
]

def parse_list(cell):
    try:
        s = (cell or "").strip()
        if not s or s.lower() in {"null", "none", "false"}:
            return []
        v = ast.literal_eval(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []

def avg(xs): return round(sum(xs)/len(xs), 2) if xs else 0.0
def safe_max(xs): return max(xs) if xs else 0

def count_rows_cols(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        try:
            header = next(r)
        except StopIteration:
            return 0, 0
        rows = sum(1 for _ in r)
        return rows, len(header)

def summarize_movies_metadata(p: Path):
    # entries per movie = genres + prod_companies + prod_countries + spoken_langs
    entries, n = [], 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            e = 0
            e += len(parse_list(row.get("genres", "")))
            e += len(parse_list(row.get("production_companies", "")))
            e += len(parse_list(row.get("production_countries", "")))
            e += len(parse_list(row.get("spoken_languages", "")))
            entries.append(e)
    return n, avg(entries), safe_max(entries)

def summarize_credits(p: Path):
    # entries per movie = cast + crew
    entries, n = [], 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            e = len(parse_list(row.get("cast", ""))) + len(parse_list(row.get("crew", "")))
            entries.append(e)
    return n, avg(entries), safe_max(entries)

def summarize_keywords(p: Path):
    # entries per movie = #keywords
    entries, n = [], 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            e = len(parse_list(row.get("keywords", "")))
            entries.append(e)
    return n, avg(entries), safe_max(entries)

def summarize_ratings(p: Path):
    # entries per movie = #ratings for that movie
    counts = defaultdict(int)
    total = 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            counts[row["movieId"]] += 1
    per_movie = list(counts.values())
    return len(per_movie), avg(per_movie), safe_max(per_movie)

def summarize_links(p: Path):
    # entries per movie = 1 (mapping row)
    rows = 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for _ in r:
            rows += 1
    # avg/max are both 1.0 here, but we still print them for consistency
    return rows, 1.0, 1

def bar(value, max_value, width=40):
    if max_value <= 0: return ""
    n = int(round((value / max_value) * width))
    return "█" * max(n, 1)  # at least 1 block if value > 0

def main():
    # 1) rows/cols
    print(f"{'file':45} {'rows':>12} {'cols':>6}")
    print("-"*65)
    rc = {}
    for name in FILES:
        p = DATA_DIR / name
        if not p.exists():
            print(f"{name:45} MISSING")
            continue
        rows, cols = count_rows_cols(p)
        rc[name] = (rows, cols)
        print(f"{name:45} {rows:12,d} {cols:6d}")
    print("-"*65)

    # 2) per-file "entries per movie"
    summaries = []
    for name in FILES:
        p = DATA_DIR / name
        if not p.exists(): continue
        if name == "movies_metadata.csv":
            n, a, m = summarize_movies_metadata(p)
            label = "movies_metadata"
        elif name == "credits.csv":
            n, a, m = summarize_credits(p)
            label = "credits"
        elif name == "keywords.csv":
            n, a, m = summarize_keywords(p)
            label = "keywords"
        elif name == "ratings.csv":
            n, a, m = summarize_ratings(p)
            label = "ratings"
        elif name == "links.csv":
            n, a, m = summarize_links(p)
            label = "links"
        else:
            continue
        summaries.append((label, n, a, m))

    # print one-liners
    for label, n, a, m in summaries:
        print(f"{label}.csv ({n} movies): entries avg={a}, max={m}")

    # 3) text bars comparing AVG entries per movie
    max_avg = max((a for _,_,a,_ in summaries), default=0)
    print("\nAverage 'entries per movie' (bigger bar = feels wider):")
    for label, _, a, _ in sorted(summaries, key=lambda x: x[2], reverse=True):
        print(f"{label:16} {a:>10}  {bar(a, max_avg)}")

if __name__ == "__main__":
    main()
