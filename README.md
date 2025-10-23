# TDT4225 Assignment 3 - MongoDB Movie Database

## Setup

1. **Install dependencies:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Start MongoDB:**

    ```bash
    docker-compose up -d mongodb
    ```

3. **Clean and load data:**

    ```bash
    python clean.py
    python load_movies.py
    ```

4. **Test connection:**
    ```bash
    python example.py
    ```

## Configuration

-   **MongoDB**: localhost:27017

## Data Files

-   Raw CSV files in `data/movies/`
-   Cleaned JSONL files in `clean_out/`
-   Collections: movies, credits, keywords, links, ratings
