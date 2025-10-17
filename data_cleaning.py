import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"

def clean_movies_metadata():
    path = DATA_DIR / "movies_metadata.csv"
    df = pd.read_csv(path, low_memory=False)

    # --- Drop duplicates ---
    df = df.drop_duplicates(subset=["id"], keep="first")

    # --- Fix and clean numeric columns ---
    numeric_cols = ["budget", "revenue", "runtime", "vote_average", "vote_count", "popularity"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace 0 with NaN in budget, revenue, runtime
    df.loc[df["budget"] == 0, "budget"] = pd.NA
    df.loc[df["revenue"] == 0, "revenue"] = pd.NA
    df.loc[df["runtime"] == 0, "runtime"] = pd.NA

    # --- Clean release_date ---
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

    # --- Fill missing categorical text values with NaN or empty string ---
    text_cols = ["title", "original_title", "overview", "status", "original_language"]
    for col in text_cols:
        df[col] = df[col].fillna("")

    # --- Drop extreme missing columns ---
    df = df.drop(columns=["homepage", "tagline"], errors="ignore")

    # --- Remove rows with no release_date or title (invalid movies) ---
    df = df.dropna(subset=["release_date", "title"])

    # --- Save cleaned version ---
    cleaned_path = DATA_DIR.parent / "cleaned" / "movies_metadata_clean.csv"
    cleaned_path.parent.mkdir(exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    print(f"✅ Cleaned movies_metadata saved to: {cleaned_path}")
    print(f"Remaining rows: {len(df)}")


def clean_credits():
    path = DATA_DIR / "credits.csv"
    df = pd.read_csv(path)
    # Drop rows missing cast and crew
    df = df.dropna(subset=["cast", "crew"])
    # Remove empty lists (like "[]")
    df = df[df["cast"].str.len() > 2]
    df = df[df["crew"].str.len() > 2]

    cleaned_path = DATA_DIR.parent / "cleaned" / "credits_clean.csv"
    cleaned_path.parent.mkdir(exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    print(f"✅ Cleaned credits saved to: {cleaned_path}")
    print(f"Remaining rows: {len(df)}")


def clean_keywords():
    path = DATA_DIR / "keywords.csv"
    df = pd.read_csv(path)
    # Drop rows with no keywords
    df = df[df["keywords"].str.len() > 2]

    cleaned_path = DATA_DIR.parent / "cleaned" / "keywords_clean.csv"
    cleaned_path.parent.mkdir(exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    print(f"✅ Cleaned keywords saved to: {cleaned_path}")
    print(f"Remaining rows: {len(df)}")


def clean_links():
    path = DATA_DIR / "links.csv"
    df = pd.read_csv(path)
    # Drop rows missing tmdbId or imdbId
    df = df.dropna(subset=["tmdbId", "imdbId"])
    # Remove duplicates on movieId
    df = df.drop_duplicates(subset=["movieId"], keep="first")

    cleaned_path = DATA_DIR.parent / "cleaned" / "links_clean.csv"
    cleaned_path.parent.mkdir(exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    print(f"✅ Cleaned links saved to: {cleaned_path}")
    print(f"Remaining rows: {len(df)}")


def clean_ratings():
    path = DATA_DIR / "ratings.csv"
    df = pd.read_csv(path)
    # Drop invalid or missing ratings
    df = df.dropna(subset=["rating"])
    df = df[(df["rating"] >= 0.5) & (df["rating"] <= 5.0)]
    cleaned_path = DATA_DIR.parent / "cleaned" / "ratings_clean.csv"
    cleaned_path.parent.mkdir(exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    print(f"✅ Cleaned ratings saved to: {cleaned_path}")
    print(f"Remaining rows: {len(df)}")


if __name__ == "__main__":
    clean_movies_metadata()
    clean_credits()
    clean_keywords()
    clean_links()
    clean_ratings()
