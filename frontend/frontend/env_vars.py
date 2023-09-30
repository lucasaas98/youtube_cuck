import os
from dotenv import load_dotenv

env_file = os.getenv("ENV_FILE")
load_dotenv(dotenv_path=env_file)

PORT = os.getenv("PORT")
BACKEND_URL = os.getenv("BACKEND_URL")
BACKEND_PORT = os.getenv("BACKEND_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DATA_FOLDER = os.getenv("DATA_FOLDER")