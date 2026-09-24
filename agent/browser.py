from playwright.sync_api import sync_playwright

URL = "https://claude.ai/artifact/F3cXVQQCWCeon9QLjKJojQ#blank"


def start_browser(p, url=URL, headless=False):
    """Open a browser, go to the app, and return (browser, app_frame).
    Uses Playwright's Chromium if installed, otherwise falls back to Microsoft Edge."""
    try:
        browser = p.chromium.launch(headless=headless)
    except Exception:
        browser = p.chromium.launch(channel="msedge", headless=headless)
    page = browser.new_page()
    page.goto(url)
    for _ in range(30):                      # try for up to 30 seconds
        for frame in page.frames:
            if frame.locator("#m-client").count() > 0:
                return browser, frame
        page.wait_for_timeout(1000)
    raise RuntimeError("Could not find the app in any frame")


def fill_header(app, client="", tin="", summary=""):
    if client:
        app.locator("#m-client").fill(client)
    if tin:
        app.locator("#m-tin").fill(tin)
    if summary:
        app.locator("#m-summary").fill(summary)
    app.locator("#m-year").select_option("2025")


def list_sectors(app):
    """Return a list like [{'id': '1', 'name': 'Individual & Family'}, ...]."""
    buttons = app.locator(".sec-btn")
    return [{"id": buttons.nth(i).get_attribute("data-sec"),
             "name": buttons.nth(i).locator(".t").inner_text()}
            for i in range(buttons.count())]


def open_sector(app, sector_id):
    app.locator(f'.sec-btn[data-sec="{sector_id}"]').click()


def click_option(app, qid, option):
    """Select an option. Skips it if the question has disappeared from the screen."""
    button = app.locator(f'button[data-g="{qid}"][data-o="{option}"]')
    if button.count() == 0:                    # count() checks instantly, no 30-second wait
        print(f"Skipped {qid} = {option}: no longer on screen")
        return
    if button.get_attribute("aria-pressed") != "true":
        button.click()


def read_choices(app):
    """Return {question id: {"question": text, "options": [...], "multi": bool}} for choices on screen."""
    app.locator("[data-act=expand]").click()
    found = {}
    gates = app.locator("#main .gate")
    for i in range(gates.count()):
        g = gates.nth(i)
        buttons = g.locator("button[data-g]")
        qid = buttons.first.get_attribute("data-g")
        found[qid] = {
            "question": g.locator(".gq").inner_text(),
            "options": [buttons.nth(j).get_attribute("data-o") for j in range(buttons.count())],
            "multi": "is-multi" in (g.get_attribute("class") or ""),
        }
    return found


def read_texts(app):
    """Return {box id: label} for every free-text box on screen."""
    app.locator("[data-act=expand]").click()
    found = {}
    boxes = app.locator("#main textarea[data-k]")
    for i in range(boxes.count()):
        box = boxes.nth(i)
        label = box.locator("xpath=..").inner_text()   # the text next to the box
        found[box.get_attribute("data-k")] = label.strip()
    return found


def type_text(app, box_id, text):
    box = app.locator(f'textarea[data-k="{box_id}"]')
    if box.count() == 0:
        print(f"Skipped text box {box_id}: no longer on screen")
        return
    box.fill(text)


def export_json(app):
    app.locator("[data-act=export]").click()
    app.locator("#fmt-json").click()
    return app.locator("#expText").input_value()


# ---- Quick manual test: only runs when you run this file directly ----
if __name__ == "__main__":
    with sync_playwright() as p:
        browser, app = start_browser(p)
        fill_header(app, client="Test Client")
        print(list_sectors(app))

        open_sector(app, "1")
        click_option(app, "applies:1", "Yes")
        before = read_choices(app)
        click_option(app, "hasdeps", "Yes")
        after = read_choices(app)
        print("NEW questions:", [q for q in after if q not in before])

        texts = read_texts(app)
        print(len(texts), "text boxes, e.g.:", list(texts.items())[:2])
        type_text(app, list(texts)[0], "hello")

        open("test.json", "w").write(export_json(app))
        input("Press Enter to close...")
        browser.close()