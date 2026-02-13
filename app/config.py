import os
from pathlib import Path

APP_NAME = "FeedApp"
DB_PATH = Path(os.getenv("DB_PATH", "feedapp.db"))
# BASE_DIR is the root of the project (parent of app/)
BASE_DIR = Path(__file__).parent.parent
