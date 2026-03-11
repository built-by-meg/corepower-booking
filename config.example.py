import os
from dotenv import load_dotenv

load_dotenv()

COREPOWER_EMAIL = os.getenv("COREPOWER_EMAIL", "")
COREPOWER_PASSWORD = os.getenv("COREPOWER_PASSWORD", "")

STUDIO_LOCATION = "Your Studio Name"

CLASSES_TO_BOOK = [
    {"day": "Tuesday", "time": "7:30 AM", "class_name": "C2"},
    {"day": "Wednesday", "time": "8:15 AM", "class_name": "Yoga Sculpt"},
    {"day": "Friday", "time": "9:00 AM", "class_name": "C2"},
]

JOIN_WAITLIST = True
