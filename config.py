import os
from dotenv import load_dotenv

load_dotenv()

MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "s4toshi11")
DISCORD_INVITE = os.getenv("DISCORD_INVITE", "https://discord.gg/EkAZWtz3wr")
MANUAL_URL = os.getenv(
    "MANUAL_URL",
    "https://teletype.in/@krutoyparen/13kAtDSwiE6",
)
DB_PATH = os.getenv("DB_PATH", "applications.db")
