from playwright.sync_api import sync_playwright
from config import COREPOWER_EMAIL, COREPOWER_PASSWORD, STUDIO_LOCATION, CLASSES_TO_BOOK, JOIN_WAITLIST
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import os
import time

SESSION_FILE = Path(__file__).parent / "session.json"


def log(msg):
    print(msg, flush=True)


def dismiss_popups(page):
    """Press Escape to close modals."""
    page.keyboard.press("Escape")
    time.sleep(1)
    page.keyboard.press("Escape")
    time.sleep(1)


def dismiss_error_modals(page):
    """Dismiss 'Oops!' or other error modals that can appear after login."""
    try:
        oops = page.locator(":text('Oops')")
        if oops.count() > 0 and oops.first.is_visible(timeout=3000):
            log("  'Oops!' error detected — dismissing...")
            page.screenshot(path="screenshots/oops_error.png")
            close_btn = page.locator(
                ".cpy-modal.show button.close, .cpy-modal.show [aria-label='Close'], "
                ".modal.show button.close, .modal.show [aria-label='Close'], "
                "button:has-text('OK'), button:has-text('Close')"
            )
            if close_btn.count() > 0 and close_btn.first.is_visible(timeout=2000):
                close_btn.first.click()
            else:
                page.keyboard.press("Escape")
            time.sleep(2)
            log("  Error dismissed")
            return True
    except Exception:
        pass
    return False


def get_upcoming_dates_for_day(day_name, weeks=2):
    """Get the next N weeks' occurrences of a given weekday."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today = datetime.now()
    target_day = days.index(day_name)
    days_ahead = (target_day - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    dates = []
    for w in range(weeks):
        dates.append(today + timedelta(days=days_ahead + 7 * w))
    return dates


def format_date_header(dt):
    """Format a date to match CorePower's section headers, e.g. 'Tue, Mar 10'."""
    return dt.strftime("%a, %b %d").replace(" 0", " ")


def navigate_to_schedule(page):
    """Navigate to the CorePower schedule page and search for the studio."""
    schedule_url = "https://www.corepoweryoga.com/yoga-schedules"
    log("Step 1: Opening class schedule page...")
    page.goto(schedule_url, wait_until="networkidle")
    time.sleep(3)
    dismiss_popups(page)
    time.sleep(2)

    # If the quiz/promo overlay appeared, dismiss it and re-navigate
    schedule_sections = page.locator(".schedule-list")
    try:
        schedule_sections.first.wait_for(state="visible", timeout=3000)
    except Exception:
        log("  Schedule not visible — dismissing quiz and re-navigating...")
        try:
            maybe_later = page.locator("button:has-text('MAYBE LATER'), a:has-text('MAYBE LATER')")
            if maybe_later.count() > 0 and maybe_later.first.is_visible(timeout=3000):
                maybe_later.first.click()
                time.sleep(2)
        except Exception:
            pass
        dismiss_popups(page)
        time.sleep(1)
        page.goto(schedule_url, wait_until="networkidle")
        time.sleep(3)
        dismiss_popups(page)
        time.sleep(2)

    page.screenshot(path="screenshots/01_schedule_page.png")
    log("  Done")

    log(f"Step 2: Confirming studio filter is '{STUDIO_LOCATION}'...")

    # Check if the correct studio is already filtered via the chip
    correct_filter = False
    chip_text_el = page.locator(".cpy-chip-container .width-content")
    if chip_text_el.count() > 0:
        chip_text = chip_text_el.first.text_content().strip()
        if STUDIO_LOCATION.lower() in chip_text.lower():
            correct_filter = True
            log(f"  Filter already set to '{chip_text}'")
        else:
            log(f"  Wrong filter: '{chip_text}' — clearing and re-searching...")
            close_icon = page.locator(".cpy-chip-container img[alt='Close icon']")
            if close_icon.count() > 0 and close_icon.first.is_visible(timeout=3000):
                close_icon.first.click()
                time.sleep(3)

    if not correct_filter:
        log(f"  Searching for {STUDIO_LOCATION}...")
        search_input = page.locator(
            "input[placeholder*='Studio'], input[placeholder*='studio'], "
            "input[placeholder*='city'], input[placeholder*='ZIP'], "
            "input[placeholder*='Search'], input[placeholder*='search']"
        ).first
        search_input.wait_for(state="visible", timeout=10000)
        search_input.click()
        time.sleep(1)
        search_input.fill(STUDIO_LOCATION)
        time.sleep(2)
        page.screenshot(path="screenshots/02a_search_typed.png")

        # Click the search/magnifying glass button
        search_btn = page.locator(
            "button[aria-label*='search' i], button:has(img[alt*='search' i]), "
            "svg[class*='search'], img[class*='search'], "
            "[class*='search-icon'], [class*='search-btn']"
        )
        try:
            if search_btn.count() > 0 and search_btn.first.is_visible(timeout=3000):
                search_btn.first.click()
                log("  Clicked search button")
                time.sleep(4)
        except Exception:
            pass

        # Look for the studio in search results and click it
        page.screenshot(path="screenshots/02b_search_results.png")
        studio_link = page.locator(f"a:has-text('{STUDIO_LOCATION}')")
        try:
            if studio_link.count() > 0 and studio_link.first.is_visible(timeout=5000):
                studio_link.first.click()
                log(f"  Clicked '{STUDIO_LOCATION}' link")
                time.sleep(4)
        except Exception:
            search_input.press("Enter")
            time.sleep(4)

    # Wait for schedule to load
    schedule_sections = page.locator(".schedule-list")
    try:
        schedule_sections.first.wait_for(state="visible", timeout=10000)
    except Exception:
        log("  WARNING: Schedule sections not visible after search")

    page.screenshot(path="screenshots/02_schedule_loaded.png")
    log("  Done — schedule loaded!")


def scroll_to_date_section(page, target_date):
    """Scroll incrementally to the target date section to trigger lazy loading."""
    date_str = format_date_header(target_date)
    log(f"Step 3: Scrolling to {date_str}...")

    # Scroll down incrementally to trigger lazy-loaded class cards
    for _ in range(30):
        page.mouse.wheel(0, 800)
        time.sleep(0.5)
        header = page.locator(f"p.schedule-list__date:has-text('{date_str}')")
        if header.count() > 0 and header.is_visible():
            break

    # Now scroll the header into view precisely
    date_header = page.locator(f"p.schedule-list__date:has-text('{date_str}')")
    try:
        date_header.scroll_into_view_if_needed(timeout=5000)
        time.sleep(3)

        class_count_el = date_header.locator("xpath=../.. >> span.schedule-list__class-count")
        if class_count_el.count() == 0:
            class_count_el = page.locator(
                f"text='{date_str}' >> xpath=../../.. >> span.schedule-list__class-count"
            )
        count_text = class_count_el.first.text_content(timeout=3000) if class_count_el.count() > 0 else "unknown"
        log(f"  Found section: {date_str} — {count_text}")

        # If 0 classes, wait and re-check — they may still be loading
        if "0 classes" in str(count_text):
            log("  Waiting for classes to load...")
            time.sleep(5)
            page.mouse.wheel(0, 200)
            time.sleep(3)
    except Exception as e:
        log(f"  Could not find date section for {date_str}: {e}")

    page.screenshot(path="screenshots/03_target_day.png")


MAX_TIME_DIFF_MINUTES = 90


def parse_time_minutes(time_str):
    """Parse '7:30 am' into minutes since midnight."""
    t = time_str.strip().lower()
    is_pm = "pm" in t
    t = t.replace("am", "").replace("pm", "").strip()
    hours, minutes = int(t.split(":")[0]), int(t.split(":")[1])
    if is_pm and hours != 12:
        hours += 12
    elif not is_pm and hours == 12:
        hours = 0
    return hours * 60 + minutes


def find_and_book_class(page, class_name, class_time, target_date):
    """
    Find the best BOOK button for a class on a specific date.
    Matches by class name, then picks the time slot closest to the preferred time.
    Falls back to any bookable slot within MAX_TIME_DIFF_MINUTES.
    """
    date_str = format_date_header(target_date)
    target_minutes = parse_time_minutes(class_time)
    log(f"Step 4: Looking for {class_name} near {class_time.lower()} in {date_str} section...")

    date_scope = f".schedule-list:has(.schedule-list__date:has-text('{date_str}'))"
    rows = page.locator(f"{date_scope} .session-row-view:has(:text('{class_name}'))")
    count = rows.count()
    log(f"  Found {count} '{class_name}' row(s) on {date_str}")

    if count == 0:
        log(f"  No rows matched — dumping HTML for debugging")
        dump_page_html(page)
        page.screenshot(path="screenshots/04_no_book_found.png")
        return False

    # Collect candidates: time, button, status
    candidates = []
    for j in range(count):
        row = rows.nth(j)
        try:
            time_el = row.locator("[class*='sessionTime']").first
            row_time = time_el.text_content().strip()
            row_minutes = parse_time_minutes(row_time)
            diff = abs(row_minutes - target_minutes)

            book_btn = row.locator(".btn-session-book")
            for k in range(book_btn.count()):
                btn = book_btn.nth(k)
                if btn.is_visible(timeout=1000):
                    candidates.append({
                        "time": row_time,
                        "diff": diff,
                        "btn": btn,
                        "btn_text": btn.text_content().strip(),
                    })
                    break
        except Exception:
            continue

    if not candidates:
        log(f"  Found rows but no visible buttons")
        dump_page_html(page)
        page.screenshot(path="screenshots/04_no_book_found.png")
        return False

    candidates.sort(key=lambda c: c["diff"])

    for c in candidates:
        log(f"  {class_name} at {c['time']} ({c['diff']}min off): '{c['btn_text']}'")

    # If the closest match is already booked or waitlisted, skip
    closest = candidates[0]
    closest_upper = closest["btn_text"].strip().upper()
    if "BOOKED" in closest_upper and closest_upper != "BOOK":
        log(f"  Already booked: {class_name} at {closest['time']} — skipping!")
        return "already_booked"
    if closest_upper.startswith("WAITLISTED"):
        log(f"  Already waitlisted: {class_name} at {closest['time']} ({closest['btn_text']}) — skipping!")
        return "already_waitlisted"

    # Try to book the closest bookable slot within the time window
    last_status = False
    for c in candidates:
        if c["diff"] > MAX_TIME_DIFF_MINUTES:
            break
        upper = c["btn_text"].upper()

        if "BOOK" in upper and "CLASS FULL" not in upper and "BOOKED" not in upper:
            c["btn"].scroll_into_view_if_needed()
            time.sleep(1)
            page.screenshot(path="screenshots/04_before_book_click.png")
            c["btn"].click()
            time.sleep(3)
            page.screenshot(path="screenshots/04_after_book_click.png")
            log(f"  Clicked BOOK for {class_name} at {c['time']}!")
            return True
        elif "WAITLIST" in upper:
            if JOIN_WAITLIST:
                c["btn"].scroll_into_view_if_needed()
                time.sleep(1)
                page.screenshot(path="screenshots/04_before_waitlist_click.png")
                c["btn"].click()
                time.sleep(3)
                page.screenshot(path="screenshots/04_after_waitlist_click.png")
                log(f"  Clicked JOIN WAITLIST for {class_name} at {c['time']}!")
                return "waitlist_clicked"
            if not last_status:
                last_status = "waitlist"
        elif "CLASS FULL" in upper:
            if not last_status:
                last_status = "full"
        elif "SESSION STARTED" in upper:
            if not last_status:
                last_status = "started"

    if last_status:
        log(f"  No bookable slot — closest status: {last_status}")
    else:
        log(f"  No slots within {MAX_TIME_DIFF_MINUTES}min of preferred time")
    page.screenshot(path="screenshots/04_no_book_found.png")
    return last_status or False


def dump_page_html(page):
    """Save full page HTML for debugging selectors."""
    html = page.content()
    with open("screenshots/page_html.txt", "w", encoding="utf-8") as f:
        f.write(html)
    log("  Page HTML saved to screenshots/page_html.txt")


def handle_post_book(page, context):
    """
    After clicking BOOK, detect what happened:
    - "You're In!" confirmation → booking succeeded, click I'M DONE
    - "Sign in to book classes" → need login
    - No modal → already logged in, booking may have gone through
    Returns: "confirmed", "skipped", True (login succeeded), or False (login failed)
    """
    log("Step 5: Checking post-book result...")
    time.sleep(3)

    # Check for booking/waitlist confirmation modals
    for confirm_text in ["You're In", "You're on the waitlist", "on the waitlist"]:
        try:
            confirmed = page.locator(f":text(\"{confirm_text}\")")
            if confirmed.count() > 0 and confirmed.first.is_visible(timeout=3000):
                log(f"  Confirmed — '{confirm_text}'")
                page.screenshot(path="screenshots/05_confirmed.png")
                done_btn = page.locator("button:has-text(\"I'M DONE\")")
                if done_btn.count() > 0 and done_btn.first.is_visible(timeout=3000):
                    done_btn.first.click()
                    time.sleep(2)
                else:
                    page.keyboard.press("Escape")
                    time.sleep(2)
                context.storage_state(path=str(SESSION_FILE))
                return "confirmed"
        except Exception:
            continue

    # Check for login modal
    modal = page.locator(".cpy-modal.show, .modal.show:not(.osano-cm-dialog)")
    try:
        modal.first.wait_for(state="visible", timeout=5000)
    except Exception:
        log("  No modal — already signed in, booking likely went through!")
        return "skipped"

    # Check if modal is actually a confirmation (fallback)
    modal_text = modal.first.text_content() or ""
    if "You're In" in modal_text or "waitlist" in modal_text.lower():
        log("  Confirmed (via modal text)!")
        page.screenshot(path="screenshots/05_confirmed.png")
        try:
            done_btn = modal.locator("button:has-text(\"I'M DONE\")")
            done_btn.first.click(timeout=3000)
            time.sleep(2)
        except Exception:
            page.keyboard.press("Escape")
            time.sleep(2)
        context.storage_state(path=str(SESSION_FILE))
        return "confirmed"

    # It's a login modal — proceed with login flow
    page.screenshot(path="screenshots/05a_sign_in_modal.png")

    # Step A: Click SIGN IN on the "Sign in to book classes" modal
    try:
        log("  Found 'Sign in to book classes' modal — clicking SIGN IN...")
        sign_in_btn = modal.locator("text='SIGN IN'").first
        sign_in_btn.click(timeout=5000)
        time.sleep(5)
        page.screenshot(path="screenshots/05b_login_form.png")
    except Exception as e:
        log(f"  Could not click SIGN IN in modal: {e}")
        page.screenshot(path="screenshots/05a_modal_error.png")
        return False

    # Step B: Fill in the login form
    try:
        email_field = modal.locator(
            "input[placeholder*='Email'], input[type='email'], input[name='email']"
        ).first
        email_field.wait_for(state="visible", timeout=10000)
        log("  Login form found — entering credentials...")

        email_field.click()
        time.sleep(0.5)
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        page.keyboard.type(COREPOWER_EMAIL, delay=30)
        email_field.press("Tab")
        time.sleep(1)

        password_field = modal.locator("input[type='password'], input[placeholder*='Password']").first
        password_field.click()
        time.sleep(0.5)
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        page.keyboard.type(COREPOWER_PASSWORD, delay=30)
        password_field.press("Tab")
        time.sleep(1)
        page.screenshot(path="screenshots/05c_credentials_filled.png")

        submit_btn = modal.locator(
            "button:has-text('SIGN IN'), button:has-text('Sign In'), "
            "button[type='submit']"
        ).first
        submit_btn.click()
        log("  Submitted login!")

        page.wait_for_load_state("domcontentloaded")
        time.sleep(5)
        page.screenshot(path="screenshots/05d_after_login.png")
        log(f"  Post-login URL: {page.url}")

        context.storage_state(path=str(SESSION_FILE))
        log(f"  Session saved to {SESSION_FILE.name}")
        return True
    except Exception as e:
        log(f"  Login form error: {e}")
        page.screenshot(path="screenshots/05_login_error.png")
        return False


def book_class(page, context, class_info, target_date):
    """Full flow to book a single class on a specific date."""
    log(f"\n{'='*60}")
    log(f"Booking: {class_info['class_name']} at {class_info['time']} "
        f"on {target_date.strftime('%A %b %d')}")
    log(f"{'='*60}")

    scroll_to_date_section(page, target_date)
    result = find_and_book_class(page, class_info["class_name"], class_info["time"], target_date)

    if result in (True, "waitlist_clicked"):
        action = "waitlist" if result == "waitlist_clicked" else "book"
        post_result = handle_post_book(page, context)

        if post_result == "confirmed":
            log("  Booking confirmed!")
        elif post_result == "skipped":
            time.sleep(3)
            dismiss_error_modals(page)
            page.screenshot(path="screenshots/05_post_book.png")
        elif post_result is True:
            # Just logged in — dismiss errors and retry the click
            dismiss_error_modals(page)
            log("  Re-navigating to retry after login...")
            navigate_to_schedule(page)
            scroll_to_date_section(page, target_date)
            retry = find_and_book_class(
                page, class_info["class_name"], class_info["time"], target_date
            )
            if retry in (True, "waitlist_clicked"):
                time.sleep(3)
                retry_post = handle_post_book(page, context)
                if retry_post == "confirmed":
                    log("  Booking confirmed on retry!")
                else:
                    dismiss_error_modals(page)
                page.screenshot(path="screenshots/05_post_retry.png")
            else:
                log(f"  Retry result: {retry}")
                page.screenshot(path="screenshots/05_retry_failed.png")
        else:
            log("  Login failed — cannot complete booking")
            return "error"

        log(f"  Result URL: {page.url}")
        return "waitlist_joined" if action == "waitlist" else "booked"
    elif result in ("already_booked", "already_waitlisted"):
        return result
    elif result == "full":
        return "full"
    elif result == "waitlist":
        return "waitlist"
    elif result == "started":
        return "started"
    return "not_found"


DAY_ALIASES = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}


def build_bookings(day_filter=None, week="both"):
    """Build the list of (class_info, target_date) tuples based on filters."""
    if week == "this":
        weeks = 1
    elif week == "next":
        weeks = 1
    else:
        weeks = 2

    bookings = []
    for class_info in CLASSES_TO_BOOK:
        if day_filter and class_info["day"] not in day_filter:
            continue
        dates = get_upcoming_dates_for_day(class_info["day"], weeks=weeks if week != "next" else 2)
        if week == "next":
            dates = dates[1:]  # skip this week, take only next week
        for target_date in dates:
            bookings.append((class_info, target_date))

    bookings.sort(key=lambda b: b[1])
    return bookings


def run(bookings):
    if not COREPOWER_EMAIL or "@" not in COREPOWER_EMAIL:
        log("ERROR: COREPOWER_EMAIL not set or invalid.")
        log("Create a .env file in this directory with:")
        log("  COREPOWER_EMAIL=your_email@example.com")
        log("  COREPOWER_PASSWORD=your_password")
        log("See .env.example for reference.")
        return

    if not bookings:
        log("No classes to book with the given filters.")
        return

    log("Classes to book:")
    for class_info, target_date in bookings:
        log(f"  {target_date.strftime('%a %b %d')} {class_info['time']} {class_info['class_name']}")
    log("")

    with sync_playwright() as p:
        headless = os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true"
        log(f"Launching browser (headless={headless})...")
        browser = p.chromium.launch(headless=headless)

        if SESSION_FILE.exists():
            log(f"  Loading saved session from {SESSION_FILE.name}...")
            context = browser.new_context(
                storage_state=str(SESSION_FILE),
                viewport={"width": 1280, "height": 800},
            )
        else:
            log("  No saved session — will log in fresh")
            context = browser.new_context(viewport={"width": 1280, "height": 800})

        page = context.new_page()
        navigate_to_schedule(page)

        results = []
        needs_nav = False
        for i, (class_info, target_date) in enumerate(bookings):
            try:
                if needs_nav:
                    navigate_to_schedule(page)
                    needs_nav = False
                result = book_class(page, context, class_info, target_date)
                results.append((class_info, target_date, result))
                if result == "error":
                    needs_nav = True
            except Exception as e:
                log(f"  Error booking {class_info}: {e}")
                results.append((class_info, target_date, "error"))
                page.screenshot(path=f"screenshots/error_{class_info['day'].lower()}_{target_date.strftime('%b%d')}.png")
                needs_nav = True

        status_labels = {
            "booked": "BOOKED",
            "already_booked": "ALREADY BOOKED",
            "already_waitlisted": "ALREADY WAITLISTED",
            "full": "CLASS FULL",
            "waitlist": "WAITLIST (skipped)",
            "waitlist_joined": "JOINED WAITLIST",
            "started": "SESSION STARTED",
            "not_found": "NOT FOUND",
            "error": "ERROR",
        }
        log(f"\n{'='*60}")
        log("RESULTS:")
        for class_info, target_date, result in results:
            label = status_labels.get(result, result)
            date_str = target_date.strftime("%a %b %d")
            log(f"  {date_str} {class_info['time']} {class_info['class_name']}: {label}")
        log(f"{'='*60}")

        page.screenshot(path="screenshots/06_final.png")
        log("\nKeeping browser open for 10 seconds...")
        time.sleep(10)
        browser.close()
        log("Done!")


FILLER_WORDS = {"book", "classes", "class", "and", "for", "the", "my", "all", "week", "weeks"}


def parse_natural_args(tokens):
    """Parse natural-language-ish tokens into (week, day_filter)."""
    week = "both"
    day_filter = []

    for token in tokens:
        t = token.lower().rstrip("'s")  # handle "wednesday's", "tuesdays"
        if t in ("this",):
            week = "this"
        elif t in ("next",):
            week = "next"
        elif t in ("both",):
            week = "both"
        elif t in DAY_ALIASES:
            day_filter.append(DAY_ALIASES[t])
        elif t in FILLER_WORDS:
            continue

    return week, day_filter or None


def main():
    parser = argparse.ArgumentParser(
        description="Book CorePower Yoga classes",
        epilog="Examples:\n"
               "  book_classes.py                                  # all classes, both weeks\n"
               "  book_classes.py this                             # this week\n"
               "  book_classes.py next                             # next week\n"
               "  book_classes.py friday                           # Friday, both weeks\n"
               "  book_classes.py this friday                      # this Friday\n"
               "  book_classes.py next tuesday and wednesday       # next Tue + Wed\n"
               "  book_classes.py book next week                   # next week\n"
               "  book_classes.py book this friday and tuesday     # this Fri + Tue\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "words", nargs="*",
        help="Just type naturally: 'next friday', 'this tue and wed', 'book next week', etc.",
    )
    parsed = parser.parse_args()

    week, day_filter = parse_natural_args(parsed.words or [])
    bookings = build_bookings(day_filter=day_filter, week=week)
    run(bookings)


if __name__ == "__main__":
    main()
