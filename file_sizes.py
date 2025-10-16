from pathlib import Path
import csv
import ast
from collections import defaultdict
from datetime import datetime

# ---------------- CONFIG ----------------
DATA_DIR = Path("/Users/saraostdahl/development/TDT4225/tdt4225-assignment3/data/raw")

# Set to True for faster dev runs (uses ratings_small.csv)
USE_RATINGS_SMALL = False

FILES = [
    "movies_metadata.csv",
    "credits.csv",
    "keywords.csv",
    "links.csv",
    "ratings_small.csv" if USE_RATINGS_SMALL else "ratings.csv",
]

# --------------- UTILITIES ---------------
def as_str(x):
    """Return a string for whitespace/emptiness checks; handles None safely."""
    return "" if x is None else str(x)

def to_float_safe(x):
    """Parse float; returns None on failure (handles None/blank/garbage)."""
    try:
        s = as_str(x).strip()
        return float(s) if s else None
    except Exception:
        return None

def parse_list(cell):
    """
    Parse JSON-ish cell (single quotes, null/None/False). Always return a list.
    """
    try:
        s = as_str(cell).strip()
        if not s or s.lower() in {"null", "none", "false"}:
            return []
        v = ast.literal_eval(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []

def avg(xs):
    return round(sum(xs) / len(xs), 2) if xs else 0.0

def safe_max(xs):
    return max(xs) if xs else 0

def bar(value, max_value, width=40):
    if max_value <= 0:
        return ""
    n = int(round((value / max_value) * width))
    return "█" * max(n, 1) if value > 0 else ""

def count_rows_cols(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        try:
            header = next(r)
        except StopIteration:
            return 0, 0
        rows = sum(1 for _ in r)  # excludes header
        return rows, len(header)

# --------------- SUMMARIES ---------------
def summarize_movies_metadata(p: Path):
    """
    entries per movie = genres + prod_companies + prod_countries + spoken_langs
    Also returns simple missingness for core fields.
    """
    entries, n = [], 0
    # missingness counters
    miss_release, miss_runtime, miss_budget, miss_revenue = 0, 0, 0, 0
    zero_runtime, zero_budget, zero_revenue = 0, 0, 0
    bad_dates = 0

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

            # release_date
            rd = as_str(row.get("release_date")).strip()
            if not rd:
                miss_release += 1
            else:
                try:
                    datetime.strptime(rd, "%Y-%m-%d")
                except Exception:
                    bad_dates += 1

            # numeric fields
            runtime = to_float_safe(row.get("runtime"))
            if runtime is None:
                miss_runtime += 1
            elif runtime == 0:
                zero_runtime += 1

            budget = to_float_safe(row.get("budget"))
            if budget is None:
                miss_budget += 1
            elif budget == 0:
                zero_budget += 1

            revenue = to_float_safe(row.get("revenue"))
            if revenue is None:
                miss_revenue += 1
            elif revenue == 0:
                zero_revenue += 1

    summary = {
        "movies": n,
        "avg_entries": avg(entries),
        "max_entries": safe_max(entries),
        "missing": {
            "release_date_blank": miss_release,
            "release_date_badformat": bad_dates,
            "runtime_missing": miss_runtime,
            "runtime_zero": zero_runtime,
            "budget_missing": miss_budget,
            "budget_zero": zero_budget,
            "revenue_missing": miss_revenue,
            "revenue_zero": zero_revenue,
        }
    }
    return summary

def summarize_credits(p: Path):
    """
    entries per movie = cast + crew
    """
    entries, n = [], 0
    cast_n, crew_n = [], []
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            c = len(parse_list(row.get("cast", "")))
            k = len(parse_list(row.get("crew", "")))
            entries.append(c + k)
            cast_n.append(c)
            crew_n.append(k)
    return {
        "movies": n,
        "avg_entries": avg(entries),
        "max_entries": safe_max(entries),
        "cast_avg": avg(cast_n), "cast_max": safe_max(cast_n),
        "crew_avg": avg(crew_n), "crew_max": safe_max(crew_n),
    }

def summarize_keywords(p: Path):
    """
    entries per movie = #keywords
    """
    entries, n = [], 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            e = len(parse_list(row.get("keywords", "")))
            entries.append(e)
    return {"movies": n, "avg_entries": avg(entries), "max_entries": safe_max(entries)}

def summarize_ratings(p: Path):
    """
    entries per movie = #ratings for that MovieLens movieId
    """
    counts = defaultdict(int)
    total = 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            counts[row["movieId"]] += 1
    per_movie = list(counts.values())
    return {
        "movies": len(per_movie),
        "avg_entries": avg(per_movie),
        "max_entries": safe_max(per_movie),
        "total_rows": total
    }

def summarize_links(p: Path):
    """
    Treat as mapping per movie. Entries per movie ~ 1.
    Also compute % rows where tmdbId present.
    """
    rows = 0
    movieIds = set()
    tmdb_present = 0
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            movieIds.add(row.get("movieId"))
            if as_str(row.get("tmdbId")).strip():
                tmdb_present += 1
    pct = round(100 * tmdb_present / rows, 2) if rows else 0.0
    return {"movies": len(movieIds), "avg_entries": 1.0, "max_entries": 1, "rows": rows, "tmdb_pct": pct}

# ----------- ID JOIN COVERAGE -----------
def id_coverage(movies_path: Path, credits_path: Path, keywords_path: Path, links_path: Path, ratings_path: Path):
    """
    Simple ID sanity:
      - % of credits.id present in movies.id
      - % of keywords.id present in movies.id
      - For ratings: % of unique movieIds that have a tmdbId in links
    """
    # movies ids (tmdbId) as strings
    movies_ids = set()
    with movies_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            movies_ids.add(as_str(row.get("id")).strip())

    # credits ids present in movies
    cred_total, cred_in_movies = 0, 0
    with credits_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cid = as_str(row.get("id")).strip()
            if not cid:
                continue
            cred_total += 1
            if cid in movies_ids:
                cred_in_movies += 1

    # keywords ids present in movies
    key_total, key_in_movies = 0, 0
    with keywords_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            kid = as_str(row.get("id")).strip()
            if not kid:
                continue
            key_total += 1
            if kid in movies_ids:
                key_in_movies += 1

    # links map: movieId -> tmdbId
    ml_to_tmdb = {}
    with links_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ml_to_tmdb[as_str(row.get("movieId")).strip()] = as_str(row.get("tmdbId")).strip()

    # ratings movieIds that map to a tmdbId
    uniq_rating_movies = set()
    map_ok, map_total = 0, 0
    with ratings_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            mid = as_str(row.get("movieId")).strip()
            if not mid:
                continue
            if mid not in uniq_rating_movies:
                uniq_rating_movies.add(mid)
                map_total += 1
                if ml_to_tmdb.get(mid):
                    map_ok += 1

    return {
        "credits_in_movies_pct": round(100 * cred_in_movies / cred_total, 2) if cred_total else 0.0,
        "keywords_in_movies_pct": round(100 * key_in_movies / key_total, 2) if key_total else 0.0,
        "ratings_movieIds_with_tmdb_pct": round(100 * map_ok / map_total, 2) if map_total else 0.0
    }

# ----------------- MAIN -----------------
def main():
    # 1) rows/cols
    print(f"{'file':60} {'rows':>12} {'cols':>6}")
    print("-"*82)
    rc = {}
    for name in FILES:
        p = DATA_DIR / name
        if not p.exists():
            print(f"{name:60} MISSING")
            continue
        rows, cols = count_rows_cols(p)
        rc[name] = (rows, cols)
        print(f"{name:60} {rows:12,d} {cols:6d}")
    print("-"*82)

    # 2) one-liners (entries per movie)
    results = {}

    p = DATA_DIR / "movies_metadata.csv"
    if p.exists():
        m = summarize_movies_metadata(p)
        results["movies_metadata"] = m
        print(f"movies_metadata.csv ({m['movies']} movies): entries avg={m['avg_entries']}, max={m['max_entries']}")
        # Uncomment if you also want to print missingness/sanity:
        # print(f"  missing/sanity: {m['missing']}")

    p = DATA_DIR / "credits.csv"
    if p.exists():
        c = summarize_credits(p)
        results["credits"] = c
        print(
            f"credits.csv ({c['movies']} movies): "
            f"cast avg={c['cast_avg']}, max={c['cast_max']} | "
            f"crew avg={c['crew_avg']}, max={c['crew_max']}  "
            f"(entries avg={c['avg_entries']}, max={c['max_entries']})"
        )

    p = DATA_DIR / "keywords.csv"
    if p.exists():
        k = summarize_keywords(p)
        results["keywords"] = k
        print(f"keywords.csv ({k['movies']} movies): keywords avg={k['avg_entries']}, max={k['max_entries']}")

    p = DATA_DIR / ("ratings_small.csv" if USE_RATINGS_SMALL else "ratings.csv")
    if p.exists():
        rsum = summarize_ratings(p)
        results["ratings"] = rsum
        print(
            f"{p.name} ({rsum['movies']} movies): "
            f"ratings avg={rsum['avg_entries']} per movie, max={rsum['max_entries']}"
        )

    p = DATA_DIR / "links.csv"
    if p.exists():
        l = summarize_links(p)
        results["links"] = l
        print(
            f"links.csv ({l['movies']} movies): "
            f"tmdbId present on {l['tmdb_pct']}% of rows  "
            f"(entries avg={l['avg_entries']}, max={l['max_entries']})"
        )

    # 3) text bars (compare avg entries per movie)
    print("\nAverage 'entries per movie' (bigger bar = feels wider):")
    bars = []
    for label in ["ratings", "credits", "keywords", "movies_metadata", "links"]:
        if label in results:
            bars.append((label, results[label]["avg_entries"]))
    if bars:
        max_avg = max(a for _, a in bars)
        for label, a in sorted(bars, key=lambda x: x[1], reverse=True):
            print(f"{label:16} {a:>10}  {bar(a, max_avg)}")

    # 4) join coverage (IDs line up?)
    movies_p = DATA_DIR / "movies_metadata.csv"
    credits_p = DATA_DIR / "credits.csv"
    keywords_p = DATA_DIR / "keywords.csv"
    links_p = DATA_DIR / "links.csv"
    ratings_p = DATA_DIR / ("ratings_small.csv" if USE_RATINGS_SMALL else "ratings.csv")
    if movies_p.exists() and credits_p.exists() and keywords_p.exists() and links_p.exists() and ratings_p.exists():
        cov = id_coverage(movies_p, credits_p, keywords_p, links_p, ratings_p)
        print("\nID Join Coverage:")
        print(f"  credits.id present in movies.id: {cov['credits_in_movies_pct']}%")
        print(f"  keywords.id present in movies.id: {cov['keywords_in_movies_pct']}%")
        print(f"  ratings.movieId maps to tmdbId (via links): {cov['ratings_movieIds_with_tmdb_pct']}%")

    print("\nDone.")

if __name__ == "__main__":
    main()
