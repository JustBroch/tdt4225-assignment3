from pprint import pprint
from DbConnector import DbConnector
import statistics


# Part 1: Top 10 Directors by Median Revenue
class MovieQueries:
    def __init__(self):
        self.connection = DbConnector()
        self.db = self.connection.db

    def query1_top_directors_by_median_revenue(self):
        """
        Find top 10 directors (≥5 movies) by median revenue.
        Report: director name, movie count, median revenue, mean vote_average
        """
        print("\n=== Query 1: Top 10 Directors by Median Revenue ===\n")

        # Step 1: Aggregation pipeline to get all directors with their movies
        pipeline = [
            # Unwind crew array
            {"$unwind": "$crew"},
            # Filter only Directors
            {"$match": {"crew.job": "Director"}},
            # Lookup to join with movies collection
            {
                "$lookup": {
                    "from": "movies",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "movie_info",
                }
            },
            # Unwind movie_info (should be 1:1)
            {"$unwind": "$movie_info"},
            # Filter out movies with null/zero revenue
            {"$match": {"movie_info.revenue": {"$ne": None, "$gt": 0}}},
            # Group by director name
            {
                "$group": {
                    "_id": "$crew.name",
                    "movies": {
                        "$push": {
                            "revenue": "$movie_info.revenue",
                            "vote_average": "$movie_info.vote_average",
                        }
                    },
                    "movie_count": {"$sum": 1},
                }
            },
            # Filter directors with ≥ 5 movies
            {"$match": {"movie_count": {"$gte": 5}}},
            # Project needed fields
            {"$project": {"director": "$_id", "movies": 1, "movie_count": 1, "_id": 0}},
        ]

        # Execute aggregation
        results = list(self.db.credits.aggregate(pipeline))

        # Step 2: Calculate median revenue and mean vote_average in Python
        director_stats = []
        for director in results:
            revenues = [m["revenue"] for m in director["movies"]]
            vote_averages = [
                m["vote_average"]
                for m in director["movies"]
                if m["vote_average"] is not None
            ]

            median_revenue = statistics.median(revenues)
            mean_vote_avg = statistics.mean(vote_averages) if vote_averages else None

            director_stats.append(
                {
                    "director": director["director"],
                    "movie_count": director["movie_count"],
                    "median_revenue": median_revenue,
                    "mean_vote_average": (
                        round(mean_vote_avg, 2) if mean_vote_avg else None
                    ),
                }
            )

        # Step 3: Sort by median revenue (descending) and take top 10
        director_stats.sort(key=lambda x: x["median_revenue"], reverse=True)
        top_10 = director_stats[:10]

        # Step 4: Print results
        print(
            f"{'Rank':<5} {'Director':<30} {'Movies':<8} {'Median Revenue':<18} {'Mean Vote Avg':<15}"
        )
        print("-" * 90)
        for i, director in enumerate(top_10, 1):
            print(
                f"{i:<5} {director['director']:<30} {director['movie_count']:<8} "
                f"${director['median_revenue']:>15,.0f}  {director['mean_vote_average']:<15}"
            )

        return top_10

    def close(self):
        self.connection.close_connection()


def main():
    queries = None
    try:
        queries = MovieQueries()

        # Run Query 1
        queries.query1_top_directors_by_median_revenue()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if queries:
            queries.close()


if __name__ == "__main__":
    main()
