import json
import os
from dotenv import load_dotenv

load_dotenv()

COREPOWER_EMAIL = os.getenv("COREPOWER_EMAIL", "")
COREPOWER_PASSWORD = os.getenv("COREPOWER_PASSWORD", "")

STUDIO_LOCATION = os.getenv("STUDIO_LOCATION", "Your Studio Name")

_classes_json = os.getenv("CLASSES_TO_BOOK")
if _classes_json:
    CLASSES_TO_BOOK = json.loads(_classes_json)
else:
    CLASSES_TO_BOOK = [
        {"day": "Tuesday", "time": "9:00 AM", "class_name": "C2"},
    ]

JOIN_WAITLIST = os.getenv("JOIN_WAITLIST", "true").lower() == "true"
