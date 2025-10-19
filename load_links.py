import csv
from DbConnector import DbConnector
from pymongo import InsertOne

db = DbConnector().db
ops = []
ml_to_tmdb = {}

with open("path/to/links.csv", newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        movieId = int(row["movieId"])
        tmdbId = int(row["tmdbId"]) if row["tmdbId"] and row["tmdbId"].isdigit() else None
        imdbId = int(row["imdbId"]) if row["imdbId"] and row["imdbId"].isdigit() else None
        ml_to_tmdb[movieId] = tmdbId
        ops.append(InsertOne({"_id": movieId, "tmdbId": tmdbId, "imdbId": imdbId}))

# bulk in chunks for memory safety
for i in range(0, len(ops), 10000):
    db.links.bulk_write(ops[i:i+10000], ordered=False)

print(f"Inserted links: {len(ops)}")
# persist the map for later steps
import pickle; pickle.dump(ml_to_tmdb, open("ml_to_tmdb.pkl","wb"))
