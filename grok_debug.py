from playwright.sync_api import sync_playwright
import time
import re

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir="/home/roland/.local/share/ms-todo-ui-sync/playwright-profile",
        headless=False,
        viewport={"width": 1440, "height": 1000},
        ignore_https_errors=True,
    )
    page = context.pages[0] if context.pages else context.new_page()

    print("Navigating to To Do – sign in if prompted...")
    page.goto("https://to-do.live.com/tasks/", wait_until="domcontentloaded", timeout=60000)

    print("Browser is open. Please:")
    print("1. Sign in with your Microsoft account if asked")
    print("2. If already signed in but stuck → click your list name in sidebar (e.g. 'Silly feltores' or the one with 'never ending task')")
    print("3. Wait until you see your tasks loaded")
    input("Press Enter here in terminal when the task list is fully visible... ")

    # All inspection happens HERE — before context closes
    print("\nCurrent URL:", page.url)

    checkbox_count = page.locator('[role="checkbox"]').count()
    print("Number of checkboxes found:", checkbox_count)

    task_btn_locator = page.locator('button[aria-label*="task" i]')
    task_count = task_btn_locator.count()
    print("Number of buttons with 'task' in aria-label:", task_count)

    if task_count > 0:
        print("\nExact aria-labels of the task buttons:")
        for i in range(task_count):
            btn = task_btn_locator.nth(i)
            label = btn.get_attribute("aria-label") or "(no aria-label)"
            print(f"  Button {i}: {label!r}")

        print("\nAttempted title extraction (basic clean):")
        for i in range(task_count):
            label = task_btn_locator.nth(i).get_attribute("aria-label") or ""
            # Improved cleaning: strip prefix + common suffix junk
            cleaned = re.sub(r"(?i)^task\s+|\s+mark as completed.*|\s*\[object Object\].*|\s*mark as important.*$", "", label).strip()
            print(f"  Button {i} cleaned title: {cleaned!r}")

    # Sample text near checkboxes (helps if button labels are bad)
    print("\nSample text near first few checkboxes:")
    cbs = page.locator('[role="checkbox"]')
    for i in range(min(5, cbs.count())):
        cb = cbs.nth(i)
        text = cb.evaluate("""el => {
            let p = el.parentElement;
            while (p && !p.innerText.trim()) p = p.parentElement;
            return p ? p.innerText.trim().slice(0, 80) + '...' : '(no text)';
        }""")
        print(f"  Checkbox {i} nearby text: {text!r}")

    # Optional: keep browser open a bit longer to inspect manually if needed
    time.sleep(10)  # ← gives you 10 seconds to look at devtools (F12) before close

    context.close()
