import json, pickle, math, datetime
"""
load_movies.py

Utilities to read TMDB movie records from a JSON Lines file, normalize each record
to a consistent MongoDB document schema, and bulk-insert them into a MongoDB
collection via a DbConnector.


"""
from DbConnector import DbConnector
from pymongo import InsertOne

def to_float(x):
    try:
        if x in ("", "NaN", None): return None
        v = float(x)
        if math.isnan(v): return None
        return v
    except: return None

def to_int(x):
    try:
        return int(x)
    except: return None

def to_date(s):
    if not s or s in ("", "null", None): return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try: return s  # keep as ISO string for Mongo
        except: pass
    return None

def shape_movie(m):
    # enforce schema keys and types
    vote_count = to_int(m.get("vote_count"))
    vote_avg_raw = to_float(m.get("vote_average"))
    vote_avg = None if (vote_count is None or vote_count == 0) else vote_avg_raw

    return {
        "_id": to_int(m.get("id")),
        "title": m.get("title"),
        "original_title": m.get("original_title"),
        "original_language": (m.get("original_language") or "unknown"),
        "adult": bool(m.get("adult", False)),
        "video": bool(m.get("video", False)),
        "release_date": to_date(m.get("release_date")),
        "runtime": to_float(m.get("runtime")),
        "budget": to_float(m.get("budget")),
        "revenue": to_float(m.get("revenue")),
        "vote_average": vote_avg,
        "vote_count": vote_count or 0,
        "popularity": to_float(m.get("popularity")),
        "status": m.get("status"),
        "overview": m.get("overview") or None,
        "tagline": m.get("tagline") or None,
        "homepage": m.get("homepage") or None,
        "poster_path": m.get("poster_path") or None,
        "imdb_id": m.get("imdb_id") or None,
        "genres": m.get("genres") or [],
        "production_companies": m.get("production_companies") or [],
        "production_countries": m.get("production_countries") or [],
        "spoken_languages": m.get("spoken_languages") or [],
        "belongs_to_collection": m.get("belongs_to_collection") or None
    }

def load_movies(jsonl_path, only_ids=None, chunk=5000):
    db = DbConnector().db
    ops, n_seen, n_kept = [], 0, 0
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            raw = json.loads(line)
            tmdb_id = to_int(raw.get("id"))
            n_seen += 1
            if only_ids is not None and tmdb_id not in only_ids:
                continue
            doc = shape_movie(raw)
            if doc["_id"] is None: # skip broken ids
                continue
            ops.append(InsertOne(doc))
            n_kept += 1
            if len(ops) >= chunk:
                db.movies.bulk_write(ops, ordered=False)
                ops.clear()
    if ops:
        db.movies.bulk_write(ops, ordered=False)
    print(f"Movies processed: {n_seen}, inserted: {n_kept}")

if __name__ == "__main__":

    # filter only movies that exist in MovieLens links
    try:
        ml_to_tmdb = pickle.load(open("ml_to_tmdb.pkl", "rb"))
        id_filter = {t for t in ml_to_tmdb.values() if t is not None}
    except FileNotFoundError:
        id_filter = None
    load_movies("data/tmdb_movies.jsonl", only_ids=id_filter)
