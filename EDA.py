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

def inspect_nested_structure(path: Path, column_name: str, n_samples: int = 10):
    """
    Prints the structure (keys and types) of nested objects inside a JSON-like column.
    Works for credits.cast, credits.crew, movies_metadata.genres, etc.
    """
    print(f"\nInspecting structure of '{column_name}' from {path.name} (first {n_samples} non-empty rows):")
    seen_keys = set()
    count = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            arr = parse_list(row.get(column_name, ""))
            if not arr:
                continue
            for obj in arr:
                for k, v in obj.items():
                    seen_keys.add(k)
            count += 1
            if count >= n_samples:
                break

    if not seen_keys:
        print("  No keys found (empty or invalid column).")
        return

    print("  Keys found in nested objects:")
    for key in sorted(seen_keys):
        print(f"   - {key}")

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

def detailed_movies_metadata(path: Path):
    """
    Detailed EDA for movies_metadata.csv.
    Covers all 24 attributes: missingness, invalids, distributions, and summary counts.
    """

    # --- counters for categorical + list-like fields ---
    decade_counts = Counter()
    genre_counts = Counter()
    lang_counts = Counter()
    prod_company_counts = Counter()
    prod_country_counts = Counter()
    spoken_lang_counts = Counter()
    status_counts = Counter()

    # --- counters for numeric + binning ---
    runtime_bins = Counter()
    budget_bins  = Counter()
    revenue_bins = Counter()
    vote_avg_bins = Counter()
    vote_count_bins = Counter()

    # --- misc counters ---
    adult_true = 0
    video_true = 0
    collection_present = 0
    total = 0

    # --- missingness trackers ---
    fields_num = ["runtime", "budget", "revenue", "vote_average", "vote_count", "popularity"]
    fields_txt = ["title", "original_title", "overview", "tagline", "homepage", "status", "poster_path", "imdb_id"]
    fields_list = ["genres", "production_companies", "production_countries", "spoken_languages"]
    fields_other = ["adult", "video", "belongs_to_collection", "release_date", "original_language", "id"]

    miss = {f: 0 for f in fields_num + fields_txt + fields_list + fields_other}
    zero  = {f: 0 for f in fields_num}
    invalid = {"release_date": 0}

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        unique_ids = set()
        dup_id = 0

        for row in r:
            total += 1

            # --- id ---
            mid = as_str(row.get("id")).strip()
            if not mid:
                miss["id"] += 1
            elif mid in unique_ids:
                dup_id += 1
            else:
                unique_ids.add(mid)

            # --- adult / video / collection ---
            adult_val = as_str(row.get("adult")).strip().lower()
            if adult_val == "true":
                adult_true += 1
            elif adult_val == "":
                miss["adult"] += 1

            video_val = as_str(row.get("video")).strip().lower()
            if video_val == "true":
                video_true += 1
            elif video_val == "":
                miss["video"] += 1

            if as_str(row.get("belongs_to_collection")).strip():
                collection_present += 1
            else:
                miss["belongs_to_collection"] += 1

            # --- release_date ---
            rd = as_str(row.get("release_date")).strip()
            if not rd:
                miss["release_date"] += 1
            else:
                try:
                    dt = datetime.strptime(rd, "%Y-%m-%d")
                    decade_counts[(dt.year // 10) * 10] += 1
                except Exception:
                    invalid["release_date"] += 1

            # --- language ---
            lang = as_str(row.get("original_language")).strip()
            if lang:
                lang_counts[lang] += 1
            else:
                miss["original_language"] += 1

            # --- genres ---
            genres = parse_list(row.get("genres", ""))
            if not genres:
                miss["genres"] += 1
            for g in genres:
                name = as_str(g.get("name")).strip()
                if name:
                    genre_counts[name] += 1

            # --- production_companies ---
            companies = parse_list(row.get("production_companies", ""))
            if not companies:
                miss["production_companies"] += 1
            for c in companies:
                name = as_str(c.get("name")).strip()
                if name:
                    prod_company_counts[name] += 1

            # --- production_countries ---
            countries = parse_list(row.get("production_countries", ""))
            if not countries:
                miss["production_countries"] += 1
            for c in countries:
                name = as_str(c.get("name")).strip()
                if name:
                    prod_country_counts[name] += 1

            # --- spoken_languages ---
            langs = parse_list(row.get("spoken_languages", ""))
            if not langs:
                miss["spoken_languages"] += 1
            for c in langs:
                name = as_str(c.get("name")).strip()
                if name:
                    spoken_lang_counts[name] += 1

            # --- status ---
            st = as_str(row.get("status")).strip()
            if st:
                status_counts[st] += 1

            # --- runtime ---
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

            # --- budget / revenue ---
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

            # --- vote_average ---
            va = to_float_safe(row.get("vote_average"))
            if va is None:
                vote_avg_bins["missing"] += 1
                miss["vote_average"] += 1
            else:
                vote_avg_bins[f"{round(va * 2)/2:.1f}"] += 1

            # --- vote_count ---
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

            # --- popularity ---
            pop = to_float_safe(row.get("popularity"))
            if pop is None:
                miss["popularity"] += 1
            elif pop == 0:
                zero["popularity"] += 1

            # --- text fields ---
            for ftxt in fields_txt:
                if as_str(row.get(ftxt)).strip() == "":
                    miss[ftxt] += 1

    # --- print results ---
    print("\n=== Detailed EDA: movies_metadata.csv ===")
    print(f"Total movies: {total:,}")
    text_hist_from_counts(decade_counts, "Movies by decade", min_share=0.01)
    text_hist_from_counts(lang_counts, "Original language (top)", min_share=0.02)
    text_hist_from_counts(genre_counts, "Genres (top)", min_share=0.02)
    text_hist_from_counts(status_counts, "Status (top)", min_share=0.02)
    text_hist_from_counts(prod_country_counts, "Production countries (top)", min_share=0.02)
    text_hist_from_counts(spoken_lang_counts, "Spoken languages (top)", min_share=0.02)
    text_hist_from_counts(prod_company_counts, "Production companies (top)", min_share=0.02)
    text_hist_from_counts(runtime_bins, "Runtime minutes (binned)")
    text_hist_from_counts(budget_bins, "Budget USD (binned)")
    text_hist_from_counts(revenue_bins, "Revenue USD (binned)")
    text_hist_from_counts(vote_avg_bins, "Vote average (0–10, 0.5 steps)")
    text_hist_from_counts(vote_count_bins, "Vote count (binned)")

    # --- Missingness summary (24 total attributes) ---
    print("\nMissingness summary — movies_metadata.csv")
    print(f"{'field':25} {'missing':>10} {'miss_%':>8} {'zero':>10} {'zero_%':>8} {'true_count':>12} {'invalid':>10}")
    all_fields = fields_other + fields_num + fields_txt + fields_list
    for f in all_fields:
        m = miss.get(f, 0)
        z = zero.get(f, 0)
        inv = invalid.get(f, 0)
        t = 0
        if f == "adult":
            t = adult_true
        elif f == "video":
            t = video_true
        elif f == "belongs_to_collection":
            t = collection_present
        elif f == "id":
            t = len(unique_ids)
        m_pct = f"{(100*m/total):.1f}%" if total else "0.0%"
        z_pct = f"{(100*z/total):.1f}%" if total else "0.0%"
        print(f"{f:25} {m:10,d} {m_pct:>8} {z:10,d} {z_pct:>8} {t:12,d} {inv:10,d}")

    print(f"\nDuplicates: {dup_id:,} duplicate IDs found.")



# --------------- CREDITS ---------------
def detailed_credits(path: Path):
    cast_sizes, crew_sizes = [], []
    has_director = 0
    director_counts = Counter()
    n = 0

    # NEW: movie id duplication/missingness
    seen_movie_ids = set()
    dup_movie_id_rows = 0
    missing_id = 0
    bad_id = 0

    # NEW: per-movie duplicate people in cast/crew
    movies_with_cast_dups = 0
    total_cast_dups = 0
    movies_with_crew_dups = 0
    total_crew_dups = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1

            # --- id checks ---
            sid = as_str(row.get("id")).strip()
            if not sid:
                missing_id += 1
            elif not sid.isdigit():
                bad_id += 1
            else:
                if sid in seen_movie_ids:
                    dup_movie_id_rows += 1
                else:
                    seen_movie_ids.add(sid)

            # --- parse lists ---
            cast = parse_list(row.get("cast", ""))
            crew = parse_list(row.get("crew", ""))

            # --- sizes ---
            cast_sizes.append(len(cast))
            crew_sizes.append(len(crew))

            # --- director presence + counts ---
            found_dir = False
            for m in crew:
                if as_str(m.get("job")).strip() == "Director":
                    found_dir = True
                    name = as_str(m.get("name")).strip()
                    if name:
                        director_counts[name] += 1
            if found_dir:
                has_director += 1

            # --- duplicate people in cast (by person id) ---
            cast_ids = [as_str(m.get("id")).strip() for m in cast if as_str(m.get("id")).strip() != ""]
            if cast_ids:
                c_dups = len(cast_ids) - len(set(cast_ids))
                if c_dups > 0:
                    movies_with_cast_dups += 1
                    total_cast_dups += c_dups

            # --- duplicate people in crew (by person id + job) ---
            # using person id alone can double-count legit multi-job entries;
            # here we detect exact person-id duplicates regardless of job.
            crew_ids = [as_str(m.get("id")).strip() for m in crew if as_str(m.get("id")).strip() != ""]
            if crew_ids:
                cr_dups = len(crew_ids) - len(set(crew_ids))
                if cr_dups > 0:
                    movies_with_crew_dups += 1
                    total_crew_dups += cr_dups

    print("\n=== Detailed EDA: credits.csv ===")
    print(f"Rows: {n:,} | missing id: {missing_id:,} | non-numeric id: {bad_id:,} | duplicate id rows: {dup_movie_id_rows:,}")
    print(f"Movies with at least one Director entry: {has_director:,} / {n:,} ({has_director / max(n,1):.1%})")
    print(f"Movies with duplicate cast person-ids: {movies_with_cast_dups:,} (total duplicate cast entries: {total_cast_dups:,})")
    print(f"Movies with duplicate crew person-ids: {movies_with_crew_dups:,} (total duplicate crew entries: {total_crew_dups:,})")

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
    rows = 0
    missing_movie_id = 0
    non_numeric_movie_id = 0
    dup_movie_id_rows = 0
    seen_movie_ids = set()

    sizes = []                 # number of keywords per movie
    kw_counts = Counter()      # global frequency of keyword names

    # entry-level quality
    total_kw_entries = 0
    kw_missing_id = 0
    kw_missing_name = 0
    kw_missing_both = 0

    # per-movie duplicate keyword ids
    movies_with_dup_kw = 0
    total_dup_kw_entries = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            mid = as_str(row.get("id")).strip()
            if not mid:
                missing_movie_id += 1
            elif not mid.isdigit():
                non_numeric_movie_id += 1
            else:
                if mid in seen_movie_ids:
                    dup_movie_id_rows += 1
                else:
                    seen_movie_ids.add(mid)

            kws = parse_list(row.get("keywords", ""))
            sizes.append(len(kws))

            # collect per-movie ids to detect duplicates
            ids_this_movie = []

            for k in kws:
                total_kw_entries += 1
                kid = as_str(k.get("id")).strip()
                kname = as_str(k.get("name")).strip()

                if kid == "":
                    kw_missing_id += 1
                if kname == "":
                    kw_missing_name += 1
                if kid == "" and kname == "":
                    kw_missing_both += 1

                if kname:
                    kw_counts[kname.lower().strip()] += 1  # normalized global count

                if kid != "":
                    ids_this_movie.append(kid)

            if ids_this_movie:
                dups = len(ids_this_movie) - len(set(ids_this_movie))
                if dups > 0:
                    movies_with_dup_kw += 1
                    total_dup_kw_entries += dups

    print("\n=== Detailed EDA: keywords.csv ===")
    print(f"Rows: {rows:,} | missing movie id: {missing_movie_id:,} | non-numeric movie id: {non_numeric_movie_id:,} | duplicate movie-id rows: {dup_movie_id_rows:,}")

    # how many keywords per movie (size distribution)
    def size_bins(arr):
        b = Counter()
        for x in arr:
            if x == 0: b["0"] += 1
            elif x <= 3: b["1-3"] += 1
            elif x <= 10: b["4-10"] += 1
            else: b["11+"] += 1
        return b
    text_hist_from_counts(size_bins(sizes), "Keywords per movie")

    # per-movie duplicate keywords
    if rows:
        share_movies_with_dups = 100 * movies_with_dup_kw / rows
        print(f"Movies with duplicate keyword IDs: {movies_with_dup_kw:,} ({share_movies_with_dups:.1f}%) "
              f"(total duplicate keyword entries: {total_dup_kw_entries:,})")

    # entry-level missingness
    if total_kw_entries:
        pct_id = 100 * kw_missing_id / total_kw_entries
        pct_name = 100 * kw_missing_name / total_kw_entries
        pct_both = 100 * kw_missing_both / total_kw_entries
        print(f"Keyword entries: {total_kw_entries:,} | missing id: {kw_missing_id:,} ({pct_id:.1f}%), "
              f"missing name: {kw_missing_name:,} ({pct_name:.1f}%), "
              f"missing both: {kw_missing_both:,} ({pct_both:.1f}%)")

    # top keywords (normalized by lowercasing)
    text_hist_from_counts(kw_counts, "Top keywords", min_share=0.003)


def detailed_ratings(path: Path):
    val_counts = Counter()
    per_user = Counter()
    rows = 0
    miss_user = miss_movie = miss_rating = miss_ts = 0
    bad_user = bad_movie = bad_ts = bad_rating = 0
    allowed_ratings = {0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0}
    t_min = t_max = None

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            su, sm, sr, st = map(lambda x: as_str(row.get(x, "")).strip(), ["userId", "movieId", "rating", "timestamp"])

            # --- basic missingness ---
            if not su: miss_user += 1
            if not sm: miss_movie += 1
            if not sr: miss_rating += 1
            if not st: miss_ts += 1

            # --- validity checks ---
            if su and not su.isdigit(): bad_user += 1
            if sm and not sm.isdigit(): bad_movie += 1
            if st and not st.isdigit(): bad_ts += 1

            try:
                rv = float(sr)
                if rv not in allowed_ratings:
                    bad_rating += 1
                else:
                    val_counts[f"{rv:.1f}"] += 1
            except Exception:
                if sr: bad_rating += 1

            # --- user activity ---
            if su:
                per_user[su] += 1

            # --- timestamp range ---
            if st.isdigit():
                ts = int(st)
                t_min = ts if t_min is None else min(t_min, ts)
                t_max = ts if t_max is None else max(t_max, ts)

    print("\n=== Detailed EDA: ratings.csv ===")
    print(f"Rows: {rows:,}")
    print("Missing/invalid counts:")
    print(f"  userId    → missing: {miss_user} | non-integer: {bad_user}")
    print(f"  movieId   → missing: {miss_movie} | non-integer: {bad_movie}")
    print(f"  rating    → missing: {miss_rating} | invalid/outside 0.5–5.0: {bad_rating}")
    print(f"  timestamp → missing: {miss_ts} | non-integer: {bad_ts}")

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

    if t_min and t_max:
        print(f"Time span: {time.strftime('%Y-%m-%d', time.gmtime(t_min))} → {time.strftime('%Y-%m-%d', time.gmtime(t_max))}")

    total_rows = 26_024_289
    seen = set()
    dup_exact = 0
    rows = 0

    ''' 
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            key = (row["userId"], row["movieId"], row["rating"], row["timestamp"])
            if key in seen:
                dup_exact += 1
            else:
                seen.add(key)

            if rows % 1_000_000 == 0:
                pct = (rows / total_rows) * 100
                print(f"{pct:5.1f}% done ({rows:,}/{total_rows:,})")

    print(f"\nExact duplicate rating events: {dup_exact:,}")
    '''



# -------------- LINKS (fast) ----------------
def detailed_links(path: Path, max_examples: int = 5):
    rows = 0

    # missing/type
    miss_mid = miss_tmdb = miss_imdb = 0
    bad_mid  = bad_tmdb  = bad_imdb  = 0

    # presence
    tmdb_present = imdb_present = neither = 0

    # row-level duplicates (by value seen before)
    seen_movie_ids = set();  dup_movie_id_rows = 0
    seen_tmdb_ids  = set();  dup_tmdb_id_rows  = 0
    seen_imdb_ids  = set();  dup_imdb_id_rows  = 0

    # one-to-one conflicts (track only first value + small sample of conflicts)
    mid_first_tmdb = {}   # movieId -> first tmdbId seen
    mid_first_imdb = {}   # movieId -> first imdbId seen
    tmdb_first_mid = {}   # tmdbId  -> first movieId seen
    imdb_first_mid = {}   # imdbId  -> first movieId seen

    mid_multi_tmdb_cnt = 0; mid_multi_tmdb_examples = []
    mid_multi_imdb_cnt = 0; mid_multi_imdb_examples = []
    tmdb_multi_mid_cnt = 0; tmdb_multi_mid_examples = []
    imdb_multi_mid_cnt = 0; imdb_multi_mid_examples = []

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows += 1
            smid  = as_str(row.get("movieId")).strip()
            stmdb = as_str(row.get("tmdbId")).strip()
            simdb = as_str(row.get("imdbId")).strip()

            # missing/type (MovieLens imdbId is numeric digits *without* 'tt')
            if smid  == "": miss_mid  += 1
            if stmdb == "": miss_tmdb += 1
            if simdb == "": miss_imdb += 1

            is_mid_int  = smid.isdigit()  if smid  else False
            is_tmdb_int = stmdb.isdigit() if stmdb else False
            is_imdb_int = simdb.isdigit() if simdb else False

            if smid  and not is_mid_int:  bad_mid  += 1
            if stmdb and not is_tmdb_int: bad_tmdb += 1
            if simdb and not is_imdb_int: bad_imdb += 1

            if stmdb: tmdb_present += 1
            if simdb: imdb_present += 1
            if not stmdb and not simdb: neither += 1

            # row-level duplicates (by id value)
            if smid:
                if smid in seen_movie_ids: dup_movie_id_rows += 1
                else: seen_movie_ids.add(smid)
            if stmdb:
                if stmdb in seen_tmdb_ids: dup_tmdb_id_rows += 1
                else: seen_tmdb_ids.add(stmdb)
            if simdb:
                if simdb in seen_imdb_ids: dup_imdb_id_rows += 1
                else: seen_imdb_ids.add(simdb)

            # one-to-one conflict detection — store only first mapping
            if is_mid_int and is_tmdb_int:
                prev = mid_first_tmdb.get(smid)
                if prev is None:
                    mid_first_tmdb[smid] = stmdb
                elif prev != stmdb:
                    mid_multi_tmdb_cnt += 1
                    if len(mid_multi_tmdb_examples) < max_examples:
                        mid_multi_tmdb_examples.append((smid, prev, stmdb))
            if is_mid_int and is_imdb_int:
                prev = mid_first_imdb.get(smid)
                if prev is None:
                    mid_first_imdb[smid] = simdb
                elif prev != simdb:
                    mid_multi_imdb_cnt += 1
                    if len(mid_multi_imdb_examples) < max_examples:
                        mid_multi_imdb_examples.append((smid, prev, simdb))
            if is_tmdb_int and is_mid_int:
                prev = tmdb_first_mid.get(stmdb)
                if prev is None:
                    tmdb_first_mid[stmdb] = smid
                elif prev != smid:
                    tmdb_multi_mid_cnt += 1
                    if len(tmdb_multi_mid_examples) < max_examples:
                        tmdb_multi_mid_examples.append((stmdb, prev, smid))
            if is_imdb_int and is_mid_int:
                prev = imdb_first_mid.get(simdb)
                if prev is None:
                    imdb_first_mid[simdb] = smid
                elif prev != smid:
                    imdb_multi_mid_cnt += 1
                    if len(imdb_multi_mid_examples) < max_examples:
                        imdb_multi_mid_examples.append((simdb, prev, smid))

    # --- print summary ---
    print("\n=== Detailed EDA: links.csv (fast) ===")
    print(f"Rows: {rows:,}")
    print("Missing/invalid counts:")
    print(f"  movieId → missing: {miss_mid} | non-integer: {bad_mid}")
    print(f"  tmdbId  → missing: {miss_tmdb} | non-integer: {bad_tmdb}")
    print(f"  imdbId  → missing: {miss_imdb} | non-integer: {bad_imdb}")

    print("\nPresence:")
    print(f"  tmdbId present: {tmdb_present:,} ({(100*tmdb_present/max(rows,1)):.2f}%)")
    print(f"  imdbId present: {imdb_present:,} ({(100*imdb_present/max(rows,1)):.2f}%)")
    print(f"  neither present: {neither:,} ({(100*neither/max(rows,1)):.2f}%)")

    print("\nRow-level duplicates:")
    print(f"  duplicate movieId rows: {dup_movie_id_rows:,}")
    print(f"  duplicate tmdbId rows:  {dup_tmdb_id_rows:,}")
    print(f"  duplicate imdbId rows:  {dup_imdb_id_rows:,}")

    print("\nMapping conflicts (should be one-to-one):")
    print(f"  movieId→tmdbId conflicts: {mid_multi_tmdb_cnt}")
    if mid_multi_tmdb_examples:
        print("   examples (movieId: first_tmdbId -> other_tmdbId):")
        for smid, first_t, other_t in mid_multi_tmdb_examples:
            print(f"    {smid}: {first_t} -> {other_t}")
    print(f"  tmdbId→movieId conflicts: {tmdb_multi_mid_cnt}")
    if tmdb_multi_mid_examples:
        print("   examples (tmdbId: first_movieId -> other_movieId):")
        for t, first_m, other_m in tmdb_multi_mid_examples:
            print(f"    {t}: {first_m} -> {other_m}")
    print(f"  movieId→imdbId conflicts: {mid_multi_imdb_cnt}")
    if mid_multi_imdb_examples:
        print("   examples (movieId: first_imdbId -> other_imdbId):")
        for smid, first_i, other_i in mid_multi_imdb_examples:
            print(f"    {smid}: {first_i} -> {other_i}")
    print(f"  imdbId→movieId conflicts: {imdb_multi_mid_cnt}")
    if imdb_multi_mid_examples:
        print("   examples (imdbId: first_movieId -> other_movieId):")
        for i, first_m, other_m in imdb_multi_mid_examples:
            print(f"    {i}: {first_m} -> {other_m}")



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

  