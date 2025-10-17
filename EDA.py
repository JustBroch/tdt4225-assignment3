#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outputs include:
- Distributions for main attributes (decade, language, genres, runtime, budget, revenue, votes)
- Missingness table for movies (core numeric/text/date fields)
- Credits & keywords missingness/coverage summary
- Duplicate ID checks (movies)
- Ratings value validity + per-user activity + time span
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

def pct(x, d):
    return f"{(100 * x / max(d, 1)):.1f}%"

# --------------- MOVIES ----------------
def detailed_movies_metadata(path: Path):
    """
    Distributions for decade, language, genres, runtime, budget, revenue, votes.
    Also prints a missingness table for core fields.
    """
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

    # Missingness table accumulators
    fields_num = ["runtime", "budget", "revenue", "vote_average", "vote_count", "popularity"]
    fields_txt = ["title", "original_title", "overview", "tagline", "homepage", "status", "poster_path", "imdb_id"]
    total = 0
    miss = {f: 0 for f in fields_num + fields_txt + ["release_date"]}
    zero  = {f: 0 for f in fields_num}  # numeric zeros only
    invalid = {"release_date": 0}

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            # release_date → decade + missing/invalid
            rd = as_str(row.get("release_date")).strip()
            if not rd:
                miss_release += 1
                miss["release_date"] += 1
            else:
                try:
                    dt = datetime.strptime(rd, "%Y-%m-%d")
                    decade_counts[(dt.year // 10) * 10] += 1
                except Exception:
                    bad_dates += 1
                    invalid["release_date"] += 1

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
            if rt is None:
                runtime_bins["missing"] += 1
                miss["runtime"] += 1
            elif rt == 0:
                runtime_bins["zero"] += 1
                zero["runtime"] += 1
            elif rt < 60:
                runtime_bins["<60"] += 1
            elif rt < 90:
                runtime_bins["60-89"] += 1
            elif rt < 120:
                runtime_bins["90-119"] += 1
            elif rt < 150:
                runtime_bins["120-149"] += 1
            else:
                runtime_bins["150+"] += 1

            # money bins helper + missingness
            def money_bin(field, bins):
                x = to_float_safe(row.get(field))
                if x is None:
                    bins["missing"] += 1
                    miss[field] += 1
                elif x == 0:
                    bins["0"] += 1
                    zero[field] += 1
                elif x <= 1_000_000:
                    bins["<=1e6"] += 1
                elif x <= 10_000_000:
                    bins["1e6-1e7"] += 1
                elif x <= 100_000_000:
                    bins["1e7-1e8"] += 1
                else:
                    bins[">1e8"] += 1

            money_bin("budget", budget_bins)
            money_bin("revenue", revenue_bins)

            # vote_average (0.5 buckets) + missingness
            va = to_float_safe(row.get("vote_average"))
            if va is None:
                vote_avg_bins["missing"] += 1
                miss["vote_average"] += 1
            else:
                vote_avg_bins[f"{round(va * 2)/2:.1f}"] += 1

            # vote_count + missingness/zero
            vc = to_float_safe(row.get("vote_count"))
            if vc is None:
                vote_count_bins["missing"] += 1
                miss["vote_count"] += 1
            elif vc == 0:
                vote_count_bins["0"] += 1
                zero["vote_count"] += 1
            elif vc <= 10:
                vote_count_bins["1-10"] += 1
            elif vc <= 50:
                vote_count_bins["11-50"] += 1
            elif vc <= 200:
                vote_count_bins["51-200"] += 1
            else:
                vote_count_bins[">200"] += 1

            # popularity (only missing/zero tracked)
            pop = to_float_safe(row.get("popularity"))
            if pop is None:
                miss["popularity"] += 1
            elif pop == 0:
                zero["popularity"] += 1

            # text field missingness
            for ftxt in fields_txt:
                if as_str(row.get(ftxt)).strip() == "":
                    miss[ftxt] += 1

    # print distributions
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

    # missingness table
    print("\nMissingness summary — movies_metadata.csv")
    print(f"{'field':20} {'missing':>10} {'miss_%':>8} {'zero':>10} {'zero_%':>8} {'invalid':>10}")
    for f in ["release_date"] + fields_num + fields_txt:
        m = miss.get(f, 0)
        z = zero.get(f, 0)
        inv = invalid.get(f, 0)
        m_pct = f"{(100*m/total):.1f}%" if total else "0.0%"
        z_pct = f"{(100*z/total):.1f}%" if total else "0.0%"
        print(f"{f:20} {m:10,d} {m_pct:>8} {z:10,d} {z_pct:>8} {inv:10,d}")

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

def print_missing_credits_keywords(credits_path: Path, keywords_path: Path):
    # credits missingness
    c_total = 0; no_cast = 0; no_crew = 0; no_director = 0
    with credits_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            c_total += 1
            cast = parse_list(row.get("cast", ""))
            crew = parse_list(row.get("crew", ""))
            if len(cast) == 0: no_cast += 1
            if len(crew) == 0: no_crew += 1
            if not any(as_str(m.get("job")).strip() == "Director" for m in crew):
                no_director += 1

    # keywords missingness
    k_total = 0; no_keywords = 0
    with keywords_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            k_total += 1
            kws = parse_list(row.get("keywords", ""))
            if len(kws) == 0: no_keywords += 1

    print("\nMissingness summary — credits.csv / keywords.csv")
    print(f"credits:   rows={c_total:,} | cast==0: {no_cast:,} ({pct(no_cast, c_total)}), "
          f"crew==0: {no_crew:,} ({pct(no_crew, c_total)}), "
          f"no Director: {no_director:,} ({pct(no_director, c_total)})")
    print(f"keywords:  rows={k_total:,} | keywords==0: {no_keywords:,} ({pct(no_keywords, k_total)})")

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

def validate_rating_values(path: Path):
    """Check rating values are in the expected MovieLens set {0.5, …, 5.0}."""
    allowed = {0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0}
    bad = 0; total = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            rv = to_float_safe(row.get("rating"))
            if rv is None or rv not in allowed:
                bad += 1
    print("\nValidity — ratings.csv")
    print(f"ratings with invalid/missing value: {bad:,} / {total:,}")

# -------------- LINKS ----------------
def detailed_links(path: Path):
    rows = 0
    movie_ids = set()
    tmdb_present = 0
    imdb_present = 0
    dup_movie_ids = 0
    seen_movie_ids = set()
    neither = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            mid = as_str(row.get("movieId")).strip()
            tmdb = as_str(row.get("tmdbId")).strip()
            imdb = as_str(row.get("imdbId")).strip()

            if mid:
                if mid in seen_movie_ids:
                    dup_movie_ids += 1
                else:
                    seen_movie_ids.add(mid)
                    movie_ids.add(mid)

            if tmdb: tmdb_present += 1
            if imdb: imdb_present += 1
            if not tmdb and not imdb: neither += 1

    print("\n=== Detailed EDA: links.csv ===")
    print(f"rows={rows:,} | unique movieId={len(movie_ids):,} | duplicate movieId rows={dup_movie_ids:,}")
    if rows:
        print(f"tmdbId present: {tmdb_present:,} ({(100*tmdb_present/rows):.2f}%)")
        print(f"imdbId present: {imdb_present:,} ({(100*imdb_present/rows):.2f}%)")
        print(f"neither tmdbId nor imdbId: {neither:,} ({(100*neither/rows):.2f}%)")


# -------- duplicates & joins ----------
def check_duplicates_movies(path: Path):
    seen_tmdb = set(); dup_tmdb = 0
    seen_imdb = set(); dup_imdb = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            tm = as_str(row.get("id")).strip()
            im = as_str(row.get("imdb_id")).strip()
            if tm:
                if tm in seen_tmdb: dup_tmdb += 1
                else: seen_tmdb.add(tm)
            if im:
                if im in seen_imdb: dup_imdb += 1
                else: seen_imdb.add(im)
    print("\nDuplicates — movies_metadata.csv")
    print(f"duplicate tmdb id rows: {dup_tmdb}")
    print(f"duplicate imdb_id rows: {dup_imdb}")

# (Optional) keep full id_coverage if you want the 3-line report
def id_coverage(movies_path: Path, credits_path: Path, keywords_path: Path, links_path: Path, ratings_path: Path):
    """Full join coverage report (optional)."""
    movies_ids = set()
    with movies_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            movies_ids.add(as_str(row.get("id")).strip())

    cred_total, cred_in_movies = 0, 0
    with credits_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cid = as_str(row.get("id")).strip()
            if not cid: continue
            cred_total += 1
            if cid in movies_ids: cred_in_movies += 1

    key_total, key_in_movies = 0, 0
    with keywords_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            kid = as_str(row.get("id")).strip()
            if not kid: continue
            key_total += 1
            if kid in movies_ids: key_in_movies += 1

    ml_to_tmdb = {}
    with links_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ml_to_tmdb[as_str(row.get("movieId")).strip()] = as_str(row.get("tmdbId")).strip()

    uniq_rating_movies = set()
    map_ok, map_total = 0, 0
    with ratings_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            mid = as_str(row.get("movieId")).strip()
            if not mid: continue
            if mid not in uniq_rating_movies:
                uniq_rating_movies.add(mid)
                map_total += 1
                if ml_to_tmdb.get(mid): map_ok += 1

    print("\nID Join Coverage:")
    print(f"  credits.id present in movies.id: {(100*cred_in_movies/max(cred_total,1)):.2f}%")
    print(f"  keywords.id present in movies.id: {(100*key_in_movies/max(key_total,1)):.2f}%")
    print(f"  ratings.movieId maps to tmdbId (via links): {(100*map_ok/max(map_total,1)):.2f}%")

# ------------- PUBLIC API --------------
def run_detailed_eda(base_dir: Path, use_ratings_small: bool = False):
    # Movies
    p_movies = base_dir / "movies_metadata.csv"
    if p_movies.exists():
        detailed_movies_metadata(p_movies)
        check_duplicates_movies(p_movies)

    # Credits & keywords
    p_credits = base_dir / "credits.csv"
    p_keywords = base_dir / "keywords.csv"
    if p_credits.exists():
        detailed_credits(p_credits)
    if p_keywords.exists():
        detailed_keywords(p_keywords)
    if p_credits.exists() and p_keywords.exists():
        print_missing_credits_keywords(p_credits, p_keywords)

    # LINKS — always full
    p_links = base_dir / "links.csv"
    if p_links.exists():
        detailed_links(p_links)

    # RATINGS — always full
    p_ratings = base_dir / "ratings.csv"
    if p_ratings.exists():
        detailed_ratings(p_ratings)
        validate_rating_values(p_ratings)

    # Extended join coverage across all CSVs
    if p_movies.exists() and p_credits.exists() and p_keywords.exists() and p_links.exists() and p_ratings.exists():
        # movies ids (tmdb ids)
        movies_ids = set()
        with p_movies.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                mid = as_str(row.get("id")).strip()
                if mid:
                    movies_ids.add(mid)

        # credits.id in movies.id
        cred_total = cred_in_movies = 0
        with p_credits.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                cid = as_str(row.get("id")).strip()
                if not cid:
                    continue
                cred_total += 1
                if cid in movies_ids:
                    cred_in_movies += 1

        # keywords.id in movies.id
        key_total = key_in_movies = 0
        with p_keywords.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                kid = as_str(row.get("id")).strip()
                if not kid:
                    continue
                key_total += 1
                if kid in movies_ids:
                    key_in_movies += 1

        # links coverage vs movies (tmdbId)
        links_total = links_tmdb_present = links_tmdb_in_movies = 0
        tmdb_in_links = set()
        ml_to_tmdb = {}
        with p_links.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                links_total += 1
                mid  = as_str(row.get("movieId")).strip()
                tmdb = as_str(row.get("tmdbId")).strip()
                if mid:
                    ml_to_tmdb[mid] = tmdb
                if tmdb:
                    links_tmdb_present += 1
                    tmdb_in_links.add(tmdb)
                    if tmdb in movies_ids:
                        links_tmdb_in_movies += 1
        movies_with_link = len(movies_ids.intersection(tmdb_in_links))

        # ratings.movieId → links.tmdbId mapping and mapping into movies
        uniq_rating_movies = set()
        map_total = map_ok = map_ok_in_movies = 0
        with p_ratings.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                mid = as_str(row.get("movieId")).strip()
                if not mid or mid in uniq_rating_movies:
                    continue
                uniq_rating_movies.add(mid)
                map_total += 1
                tmdb = ml_to_tmdb.get(mid, "")
                if tmdb:
                    map_ok += 1
                    if tmdb in movies_ids:
                        map_ok_in_movies += 1

        print("\n[EDA mode] Join coverage across CSVs")
        print(f"  credits.id present in movies.id: {pct(cred_in_movies, cred_total)} ({cred_in_movies}/{cred_total})")
        print(f"  keywords.id present in movies.id: {pct(key_in_movies, key_total)} ({key_in_movies}/{key_total})")
        print(f"  links rows with tmdbId present: {pct(links_tmdb_present, links_total)} ({links_tmdb_present}/{links_total})")
        print(f"  links.tmdbId present in movies.id: {pct(links_tmdb_in_movies, links_tmdb_present)} ({links_tmdb_in_movies}/{links_tmdb_present})")
        print(f"  movies.id with a matching links.tmdbId: {pct(movies_with_link, len(movies_ids))} ({movies_with_link}/{len(movies_ids)})")
        print(f"  ratings.movieId maps to tmdbId via links: {pct(map_ok, map_total)} ({map_ok}/{map_total})")
        print(f"  ratings.movieId maps to tmdbId that exists in movies.id: {pct(map_ok_in_movies, map_total)} ({map_ok_in_movies}/{map_total})")


# ------------- CLI MODE ----------------
if __name__ == "__main__":
    run_detailed_eda(DATA_DIR)  # no small mode

