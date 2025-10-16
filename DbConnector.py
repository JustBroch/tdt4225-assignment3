# /Users/saraostdahl/development/TDT4225/tdt4225-assignment3/DbConnector.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

class DbConnector:
    """
    Connects to the MongoDB server (Docker container or NTNU VM).
    Reads credentials from .env:
      MONGO_HOST, MONGO_USER, MONGO_PASSWORD, MONGO_DATABASE
    """

    def __init__(self):
        # Load environment variables
        load_dotenv()

        host = os.getenv("MONGO_HOST", "localhost")
        user = os.getenv("MONGO_USER", "student")
        password = os.getenv("MONGO_PASSWORD", "password")
        database = os.getenv("MONGO_DATABASE", "assignment_3")

        # Build URI (no commas → no tuples)
        uri = f"mongodb://{user}:{password}@{host}/"

        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")  # verify connection
            self.db = self.client[database]
            print(f" Connected to MongoDB database: {self.db.name}")
        except Exception as e:
            print(" Failed to connect to MongoDB:", e)
            self.db = None  # prevent attribute errors

    def get_database(self):
        if self.db is None:
            raise RuntimeError("Database connection not established")
        return self.db

    def close_connection(self):
        if self.client:
            self.client.close()
            print(f" Connection to MongoDB closed")
