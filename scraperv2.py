import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime, timedelta

URL = "https://goldbroker.com/charts/gold-price/vnd?#historical-chart"

START_DATE = datetime(2023, 10, 1)
END_DATE   = datetime(2025, 10, 1)


async def scrape():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(URL, timeout=60000)

        # ---------------------------
        # HANDLE COOKIE POPUP
        # ---------------------------
        try:
            await page.locator("button:has-text('Allow all')").click(timeout=5000)
            print("[+] Cookie popup closed.")
        except:
            print("[!] Cookie popup not found.")

        # ---------------------------
        # HANDLE AD POPUP
        # ---------------------------
        try:
            await page.locator("button.pum-close").click(timeout=5000)
            print("[+] Ad popup closed.")
        except:
            print("[!] Ad popup not found.")

        # scroll down
        await page.evaluate("window.scrollTo(0, 800)")
        await page.wait_for_timeout(500)

        current = START_DATE

        while current <= END_DATE:
            print("Processing:", current.strftime("%Y-%m-%d"))

            # close ads inside loop
            try:
                await page.locator("button.pum-close").click(timeout=1000)
                print("[+] Ad popup closed inside loop.")
            except:
                pass

            # -----------------------------
            # OPEN DATE PICKER
            # -----------------------------
            date_input = page.locator("#form_xau_date")
            await date_input.click()
            await page.wait_for_timeout(300)

            # -----------------------------
            # SELECT YEAR
            # -----------------------------
            year_str = str(current.year)
            year_select = page.locator(".ui-datepicker-year")
            await year_select.select_option(year_str)

            # -----------------------------
            # SELECT MONTH
            # -----------------------------
            month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            month_str = month_names[current.month - 1]

            month_select = page.locator(".ui-datepicker-month")
            await month_select.select_option(label=month_str)

            # -----------------------------
            # SELECT DAY
            # -----------------------------
            day_str = str(current.day)
            day_locator = page.locator(f"//a[text()='{day_str}']")
            await day_locator.click()

            await page.wait_for_timeout(300)

            # -----------------------------
            # CLICK "Get value"
            # -----------------------------
            get_btn = page.locator("button.calendar-button")
            await get_btn.click()

            # -----------------------------
            # GET RESULT
            # -----------------------------
            result_span = page.locator("//*[@id='historical-chart']/section[3]/div/div/div/div/form/div[4]/span")

            try:
                await result_span.wait_for(state="visible", timeout=6000)
                value = (await result_span.inner_text()).strip()
            except:
                value = "N/A"

            print(" →", value)

            results.append({
                "date": current.strftime("%Y-%m-%d"),
                "gold_price_vnd": value
            })

            current += timedelta(days=1)
            await page.wait_for_timeout(300)

        # SAVE TO CSV
        df = pd.DataFrame(results)
        df.to_csv("gold_prices.csv", index=False)
        print("Saved: gold_prices.csv")

        await browser.close()


asyncio.run(scrape())
