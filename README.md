# CorePower Booking Automation

Automates booking CorePower Yoga classes using Playwright browser automation. Configure your studio, classes, and schedule — the script handles the rest.

## Setup

```
pip install -r requirements.txt
playwright install chromium
```

1. Copy `.env.example` to `.env` and fill in your CorePower credentials
2. Copy `config.example.py` to `config.py` and set your studio, classes, and times

## Usage

Just type naturally:

```
python book_classes.py                          # all classes, both weeks
python book_classes.py this                     # this week only
python book_classes.py next                     # next week only
python book_classes.py friday                   # Friday, both weeks
python book_classes.py this friday              # this Friday only
python book_classes.py next tuesday and wednesday   # next Tue + Wed
python book_classes.py book next week           # next week
```

## Configuration

Edit your local `config.py` (copied from `config.example.py`) to change:
- `STUDIO_LOCATION` — studio name to filter by
- `CLASSES_TO_BOOK` — list of day/time/class combos
- `JOIN_WAITLIST` — whether to auto-join waitlists (default: True)

## How it works

1. Opens the CorePower schedule page, dismisses quiz/promo overlays
2. Verifies the studio filter matches config (clears and re-searches if wrong)
3. Scrolls to each target date, finds matching classes by name
4. Picks the closest bookable time slot within 90 minutes of preferred time
5. Clicks BOOK or JOIN WAITLIST, handles login if session expired
6. Detects "You're In!" / "You're on the waitlist!" confirmation and dismisses
7. Skips classes that are already booked or waitlisted
8. Saves session cookies so future runs skip login

## Technical notes

- Python 3.13, Playwright 1.58 with Chromium
- CorePower uses Mindbody as backend — no public API, browser automation is the only path
- Session cookies saved to `session.json` (auto-created after first login)
- Debug screenshots saved to `screenshots/`
- Login form is React-controlled — uses `keyboard.type()` for character-by-character input

## DOM structure (for debugging)

- Schedule is a scrollable 2-week list. Each day: `div.schedule-list` with `p.schedule-list__date` header
- BOOK buttons are `div.btn-session-book` (styled divs, not `<button>`)
- Two buttons per row (mobile + desktop) — script clicks the first visible one
- Times are lowercase: "7:30 am"
- Class names have prefixes: e.g. "C2 - CorePower Yoga 2 - Location"
- Studio filter chip: `.cpy-chip-container`, close button: `img[alt='Close icon']`
- Login modal: `.cpy-modal.show` (not `[role='dialog']`)
- Classes lazy-load on scroll

## TODO

- Schedule the script to run automatically when new 2-week-ahead slots drop
- Add notifications (email/text) if booking fails
