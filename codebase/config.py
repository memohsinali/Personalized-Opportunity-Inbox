import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Scoring Weights (Must sum to 1.0)
WEIGHT_PROFILE_FIT = 0.40       # 40% Profile Match
WEIGHT_URGENCY = 0.35           # 35% Deadline Pressure
WEIGHT_COMPLETENESS = 0.25      # 25% Actionability & Perks
