from DbConnector import DbConnector
from pymongo import ASCENDING, DESCENDING

db = DbConnector().db

# ensure collections exist
for name in ["movies","credits","keywords","links","ratings"]:
    db.get_collection(name)

# links
db.links.create_index([("_id", ASCENDING)])
db.links.create_index([("tmdbId", ASCENDING)], sparse=True)
db.links.create_index([("imdbId", ASCENDING)], sparse=True)

# ratings
db.ratings.create_index([("userId", ASCENDING), ("movieId", ASCENDING)])
db.ratings.create_index([("tmdbId", ASCENDING)])
db.ratings.create_index([("movieId", ASCENDING)])
db.ratings.create_index([("timestamp", DESCENDING)])

print("Collections and indexes donee")
