#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clean Movies Dataset -> MongoDB-ready NDJSON (one document per line).

Outputs (in OUT_DIR):
  - clean_movies.jsonl
  - clean_credits.jsonl
  - clean_keywords.jsonl
  - clean_links.jsonl
  - clean_ratings.jsonl          (keeps only ratings that map to a valid tmdbId in links)

Notes:
- Uses only stdlib. No pandas required.
- Parsing of embedded lists uses ast.literal_eval.
- Dates normalized to ISO YYYY-MM-DD (invalid/missing -> null).
- Numeric zeros treated per your decisions (budget/revenue/runtime zeros -> null; vote_count keeps zeros).
- vote_average kept as-is; if vote_count == 0 we set vote_average to null (indicates "no votes yet").
- belongs_to_collection stays null (not []), other list fields -> [] when missing.
- credits: drop entries missing BOTH id and name; dedupe cast by person id (keep lowest order), crew by (person id, job).
- keywords: merge duplicate movie rows, dedupe items by keyword.id, drop missing id/name, lowercase name only for dedupe compare.
- links: keep first mapping per tmdbId (drop conflicting later rows), keep missing tmdbId as null.
- ratings: cast types; drop ratings whose movieId does not map to a tmdbId present in clean_links.
"""

from pathlib import Path
import csv
import json
import ast
from datetime import datetime

# -------------------- CONFIG --------------------
DATA_DIR = Path("/Users/saraostdahl/development/TDT4225/tdt4225-assignment3/data/raw")
OUT_DIR  = Path("./clean_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# File names
F_MOVIES   = "movies_metadata.csv"
F_CREDITS  = "credits.csv"
F_KEYWORDS = "keywords.csv"
F_LINKS    = "links.csv"           # use links_small.csv if you want, but final run should use links.csv
F_RATINGS  = "ratings.csv"         # for quick tests, swap to ratings_small.csv

# Outputs
O_MOVIES   = OUT_DIR / "clean_movies.jsonl"
O_CREDITS  = OUT_DIR / "clean_credits.jsonl"
O_KEYWORDS = OUT_DIR / "clean_keywords.jsonl"
O_LINKS    = OUT_DIR / "clean_links.jsonl"
O_RATINGS  = OUT_DIR / "clean_ratings.jsonl"

# ------------------------------------------------

def as_str(x):
    return "" if x is None else str(x)

def to_float_or_none(x):
    try:
        s = as_str(x).strip()
        if s == "": return None
        v = float(s)
        return v
    except Exception:
        return None

def to_int_or_none(x):
    try:
        s = as_str(x).strip()
        if s == "": return None
        return int(s)
    except Exception:
        return None

def parse_list(cell):
    """Parse JSON-ish arrays with single quotes. Always returns list."""
    try:
        s = as_str(cell).strip()
        if not s or s.lower() in {"null", "none"}:
            return []
        v = ast.literal_eval(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []

def parse_iso_date_or_none(s):
    s = as_str(s).strip()
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

# ---------------- MOVIES ----------------
def clean_movies(src: Path, dst: Path):
    seen_ids = set()    # for TMDB id duplicates
    seen_imdb = set()   # for imdb duplicates

    with src.open("r", encoding="utf-8", errors="replace", newline="") as f, \
         dst.open("w", encoding="utf-8") as out:
        r = csv.DictReader(f)
        for row in r:
            tmdb_id_raw = as_str(row.get("id")).strip()
            if not tmdb_id_raw.isdigit():
                # skip malformed ids (like '1997-08-20')
                continue
            tmdb_id = int(tmdb_id_raw)

            if tmdb_id in seen_ids:
                # skip duplicates, keep only first
                continue
            seen_ids.add(tmdb_id)
            # scalar booleans
            adult = as_str(row.get("adult")).strip().lower() == "true"
            video_raw = as_str(row.get("video")).strip().lower()
            video = False if video_raw == "" else (video_raw == "true")

            # release date
            release_date = parse_iso_date_or_none(row.get("release_date"))

            # language + titles
            original_language = as_str(row.get("original_language")).strip()
            if original_language == "":
                original_language = "unknown"

            title = as_str(row.get("title")).strip()
            original_title = as_str(row.get("original_title")).strip()
            if title == "" and original_title != "":
                title = original_title
            if title == "":
                title = None  # rare

            # numeric clean (zeros -> null for runtime/budget/revenue; vote_count keeps zeros)
            runtime = to_float_or_none(row.get("runtime"))
            if runtime is None or runtime == 0:
                runtime = None

            budget = to_float_or_none(row.get("budget"))
            if budget is None or budget == 0:
                budget = None

            revenue = to_float_or_none(row.get("revenue"))
            if revenue is None or revenue == 0:
                revenue = None

            vote_avg = to_float_or_none(row.get("vote_average"))
            vote_count = to_int_or_none(row.get("vote_count"))
            popularity = to_float_or_none(row.get("popularity"))
            # popularity: keep zeros as-is; only set missing to null (already handled)
            # vote_average: keep numeric; if no votes, set to null to mean "no rating yet"
            if vote_count is not None and vote_count == 0:
                vote_avg = None

            status = as_str(row.get("status")).strip()
            if status == "":
                status = "Released"  # default per your decision

            overview = as_str(row.get("overview")).strip() or None
            tagline  = as_str(row.get("tagline")).strip() or None
            homepage = as_str(row.get("homepage")).strip() or None
            poster   = as_str(row.get("poster_path")).strip() or None

            imdb_id = as_str(row.get("imdb_id")).strip() or None
            if imdb_id:
                if imdb_id in seen_imdb:
                    # drop later duplicate imdb rows (keep first)
                    imdb_id = None
                else:
                    seen_imdb.add(imdb_id)

            # belongs_to_collection stays null (don’t force [])
            btc_raw = as_str(row.get("belongs_to_collection")).strip()
            belongs = None if btc_raw in ("", "null", "None") else btc_raw  # keep raw JSONish string for now (or parse if you want)
            if belongs not in (None, ""):
                # try parse object if present (safe)
                try:
                    val = ast.literal_eval(belongs)
                    if isinstance(val, dict):
                        belongs = val
                    else:
                        belongs = None
                except Exception:
                    belongs = None

            # list fields -> [] if missing
            def norm_list(name):
                arr = parse_list(row.get(name, ""))
                return arr if arr else []

            genres = norm_list("genres")
            prod_companies = norm_list("production_companies")
            prod_countries = norm_list("production_countries")
            spoken_langs = norm_list("spoken_languages")

            doc = {
                "_id": int(tmdb_id_raw),                  # make tmdb id the MongoDB _id
                "title": title,
                "original_title": original_title or None,
                "original_language": original_language,
                "adult": adult,
                "video": video,
                "release_date": release_date,
                "runtime": runtime,
                "budget": budget,
                "revenue": revenue,
                "vote_average": vote_avg,
                "vote_count": vote_count,
                "popularity": popularity,
                "status": status,
                "overview": overview,
                "tagline": tagline,
                "homepage": homepage,
                "poster_path": poster,
                "imdb_id": imdb_id,
                "genres": genres,
                "production_companies": prod_companies,
                "production_countries": prod_countries,
                "spoken_languages": spoken_langs,
                "belongs_to_collection": belongs
            }
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")

# ---------------- CREDITS ----------------
def clean_credits(src: Path, dst: Path):
    seen_movie_rows = set()  # drop duplicate movie rows (44 in your EDA)

    with src.open("r", encoding="utf-8", errors="replace", newline="") as f, \
         dst.open("w", encoding="utf-8") as out:
        r = csv.DictReader(f)
        for row in r:
            tmdb_id = as_str(row.get("id")).strip()
            if not tmdb_id.isdigit():
                continue
            if tmdb_id in seen_movie_rows:
                continue
            seen_movie_rows.add(tmdb_id)

            cast_raw = parse_list(row.get("cast", ""))
            crew_raw = parse_list(row.get("crew", ""))

            # CAST: drop entries missing BOTH id and name; dedupe by person id, keep lowest order
            cast_by_id = {}
            for m in cast_raw or []:
                pid = m.get("id")
                name = (m.get("name") or "").strip()
                if (pid in (None, "")) and (name == ""):
                    continue
                order = m.get("order")
                try:
                    order = int(order) if order is not None else 10**9
                except Exception:
                    order = 10**9
                key = str(pid) if pid not in (None, "") else f"__noid__:{name}"
                if key not in cast_by_id or order < cast_by_id[key].get("order", 10**9):
                    cast_by_id[key] = {
                        "cast_id": m.get("cast_id"),
                        "character": m.get("character"),
                        "credit_id": m.get("credit_id"),
                        "gender": m.get("gender"),
                        "id": pid,
                        "name": name or None,
                        "order": order,
                        "profile_path": m.get("profile_path"),
                    }
            cast_clean = list(cast_by_id.values())

            # CREW: drop entries missing BOTH id and name; dedupe by (person id, job)
            crew_seen = set()
            crew_clean = []
            for m in crew_raw or []:
                pid = m.get("id")
                name = (m.get("name") or "").strip()
                job = (m.get("job") or "").strip()
                if (pid in (None, "")) and (name == ""):
                    continue
                key = (str(pid), job)
                if key in crew_seen:
                    continue
                crew_seen.add(key)
                crew_clean.append({
                    "credit_id": m.get("credit_id"),
                    "department": m.get("department"),
                    "gender": m.get("gender"),
                    "id": pid,
                    "job": job or None,
                    "name": name or None,
                    "profile_path": m.get("profile_path"),
                })

            doc = {
                "_id": int(tmdb_id),  # store movie id as Mongo _id for fast lookup
                "cast": cast_clean,   # keep [] if empty
                "crew": crew_clean
            }
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")

# ---------------- KEYWORDS ----------------
def clean_keywords(src: Path, dst: Path):
    # merge duplicate movie rows: union keyword ids
    merged = {}  # tmdb_id -> dict(id, keywords=[{id,name},...])
    for row in csv.DictReader(src.open("r", encoding="utf-8", errors="replace", newline="")):
        tmdb_id = as_str(row.get("id")).strip()
        if not tmdb_id.isdigit():
            continue
        kws = parse_list(row.get("keywords", ""))

        entry = merged.get(tmdb_id)
        if entry is None:
            entry = {"_id": int(tmdb_id), "keywords": []}
            merged[tmdb_id] = entry

        # dedupe within a movie by keyword.id; drop items missing id or name
        seen_kw = {str(k.get("id")) for k in entry["keywords"] if k.get("id") not in (None, "")}
        for k in kws or []:
            kid = as_str(k.get("id")).strip()
            kname = as_str(k.get("name")).strip()
            if kid == "" or kname == "":
                continue
            if kid in seen_kw:
                continue
            seen_kw.add(kid)
            entry["keywords"].append({"id": int(kid), "name": kname})

    with dst.open("w", encoding="utf-8") as out:
        for tmdb_id, doc in merged.items():
            # keep empty list [] when none
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")

# ---------------- LINKS ----------------
def clean_links(src: Path, dst: Path):
    """
    Keep first mapping per tmdbId, drop later conflicting rows.
    Keep missing tmdbId as null (can still be useful for imdb-only joins if needed).
    """
    tmdb_to_movie = {}  # tmdbId -> first movieId
    seen_rows = []      # store rows to write after resolving conflicts

    with src.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            smid  = as_str(row.get("movieId")).strip()
            stmdb = as_str(row.get("tmdbId")).strip()
            simdb = as_str(row.get("imdbId")).strip()

            mid = to_int_or_none(smid)
            tmdb = to_int_or_none(stmdb)  # may be None (219 missing)
            imdb = to_int_or_none(simdb)  # MovieLens imdbId has digits only (no 'tt')

            # Conflicts: if tmdb already seen with different movieId -> drop this row
            if tmdb is not None:
                prev = tmdb_to_movie.get(tmdb)
                if prev is None:
                    tmdb_to_movie[tmdb] = mid
                elif prev != mid:
                    # conflict -> skip
                    continue

            seen_rows.append({"_id_ml": mid, "tmdbId": tmdb, "imdbId": imdb})

    with dst.open("w", encoding="utf-8") as out:
        for doc in seen_rows:
            # use Mongo _id as MovieLens movieId for easy backref
            out.write(json.dumps({"_id": doc["_id_ml"], "tmdbId": doc["tmdbId"], "imdbId": doc["imdbId"]}) + "\n")

# ---------------- RATINGS ----------------
def clean_ratings(src: Path, dst: Path, links_path: Path):
    """
    Cast types; keep only ratings whose movieId maps to a valid tmdbId that exists in links.
    (Per your join coverage reflection: exclude the ~0.5–0.8% unjoinable rows.)
    """
    # Load ML movieId -> tmdbId map (only those with non-null tmdbId)
    ml_to_tmdb = {}
    with links_path.open("r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("tmdbId") is not None:
                ml_to_tmdb[int(d["_id"])] = int(d["tmdbId"])

    allowed = {0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0}

    with src.open("r", encoding="utf-8", errors="replace", newline="") as f, \
         dst.open("w", encoding="utf-8") as out:
        r = csv.DictReader(f)
        for row in r:
            su = to_int_or_none(row.get("userId"))
            sm = to_int_or_none(row.get("movieId"))
            sr = to_float_or_none(row.get("rating"))
            st = to_int_or_none(row.get("timestamp"))

            if None in (su, sm, sr, st):
                continue
            if sr not in allowed:
                continue

            tmdb = ml_to_tmdb.get(sm)
            if tmdb is None:
                # drop ratings that can’t be joined to tmdb/movies
                continue

            doc = {
                # Keep natural Mongo ObjectId (let mongoimport assign) or set your own if you want
                "userId": su,
                "movieId": sm,          # MovieLens id
                "tmdbId": tmdb,         # Joined TMDB id for cross-collection queries
                "rating": sr,
                "timestamp": st
            }
            out.write(json.dumps(doc) + "\n")

# ---------------- MAIN ----------------
def main():
    movies_csv   = DATA_DIR / F_MOVIES
    credits_csv  = DATA_DIR / F_CREDITS
    keywords_csv = DATA_DIR / F_KEYWORDS
    links_csv    = DATA_DIR / F_LINKS
    ratings_csv  = DATA_DIR / F_RATINGS

    print("Cleaning movies...")
    clean_movies(movies_csv, O_MOVIES)
    print(f"  -> {O_MOVIES}")

    print("Cleaning credits...")
    clean_credits(credits_csv, O_CREDITS)
    print(f"  -> {O_CREDITS}")

    print("Cleaning keywords...")
    clean_keywords(keywords_csv, O_KEYWORDS)
    print(f"  -> {O_KEYWORDS}")

    print("Cleaning links...")
    clean_links(links_csv, O_LINKS)
    print(f"  -> {O_LINKS}")

    print("Cleaning ratings (and joining to tmdbId via links)...")
    clean_ratings(ratings_csv, O_RATINGS, O_LINKS)
    print(f"  -> {O_RATINGS}")

    print("\n All done. Files ready for mongoimport, e.g.:")
    print(f"mongoimport --db your_db --collection movies   --file {O_MOVIES}   --jsonArray=false")
    print(f"mongoimport --db your_db --collection credits  --file {O_CREDITS}  --jsonArray=false")
    print(f"mongoimport --db your_db --collection keywords --file {O_KEYWORDS} --jsonArray=false")
    print(f"mongoimport --db your_db --collection links    --file {O_LINKS}    --jsonArray=false")
    print(f"mongoimport --db your_db --collection ratings  --file {O_RATINGS}  --jsonArray=false")

if __name__ == "__main__":
    main()
