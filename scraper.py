from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime, timedelta
import time
import re

# Requirement:
# Install the required packages using: pip install webdriver-manager selenium pandas

URL = "https://goldbroker.com/charts/gold-price/vnd?#historical-chart"

# Monthly from 01-Oct-2015 to 01-Oct-2025 (inclusive)
START_DATE = datetime(2015, 10, 1)
END_DATE   = datetime(2025, 10, 1)

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
driver.get(URL)

wait = WebDriverWait(driver, 20)

# ----------------------------------------------------
# STEP 1 — HANDLE COOKIE POPUP ("Allow All")
# ----------------------------------------------------
try:
    allow_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Allow all') or contains(.,'Allow All')]"))
    )
    allow_btn.click()
    print("[+] Cookie popup closed.")
except Exception:
    print("[!] Cookie popup not found.")

time.sleep(1)

# ----------------------------------------------------
# STEP 2 — HANDLE AD POPUP ("X" close icon)
# ----------------------------------------------------
try:
    close_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]"))
    )
    close_btn.click()
    print("[+] Ad popup closed.")
except Exception:
    print("[!] Ad popup not found.")

time.sleep(1)

# ----------------------------------------------------
# STEP 3 — SCROLL to the "Get daily closing gold price" section
# ----------------------------------------------------
driver.execute_script("window.scrollTo(0, 800);")
time.sleep(1)

# ----------------------------------------------------
# MAIN SCRAPING LOOP
# ----------------------------------------------------
results = []

# Helper to close ad popup (inside loop)
def close_ads_if_visible():
    try:
        close_btn = driver.find_element(By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]")
        if close_btn.is_displayed():
            driver.execute_script("arguments[0].click();", close_btn)
            print("[+] Ad popup closed inside loop.")
            time.sleep(0.5)
    except Exception:
        pass

# XPaths
RESULT_XPATH = "//*[@id='historical-chart']/section[3]/div/div/div/div/form/div[4]/span"
GET_BTN_XPATH = "//button[contains(.,'Get value') or contains(.,'Get Value') or contains(@class,'amcharts-period-input')]"
DATE_INPUT_XPATH = "//*[@id='form_xau_date']"

# helper to add one month while keeping day=1
def add_one_month(dt):
    year = dt.year + (dt.month // 12)
    month = dt.month % 12 + 1
    return datetime(year, month, 1)

current = START_DATE
while current <= END_DATE:
    print("Processing:", current.strftime("%Y-%m-%d"))

    # close any ads that popped up
    close_ads_if_visible()

    # --- locate the real date field
    date_input = wait.until(EC.element_to_be_clickable((By.XPATH, DATE_INPUT_XPATH)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
    time.sleep(0.2)

    # clear via JS and set value
    driver.execute_script("arguments[0].value = '';", date_input)
    time.sleep(0.05)

    # format for site: dd-mm-yyyy
    date_str = current.strftime("%d-%m-%Y")
    try:
        # try send_keys first
        date_input.send_keys(date_str)
    except Exception:
        # fallback to JS assignment
        driver.execute_script("arguments[0].value = arguments[1];", date_input, date_str)

    # dispatch events so site reacts
    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
    """, date_input)

    time.sleep(0.3)

    # --- click Get value and wait for the result text to update
    prev_text = ""
    try:
        prev_el = driver.find_element(By.XPATH, RESULT_XPATH)
        prev_text = prev_el.text.strip()
    except Exception:
        prev_text = ""

    value = "N/A"
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        # close any ads that reappeared before clicking
        close_ads_if_visible()

        # click Get value
        try:
            get_btn = driver.find_element(By.XPATH, GET_BTN_XPATH)
            driver.execute_script("arguments[0].click();", get_btn)
        except Exception as e:
            print(f"[!] Could not click Get value (attempt {attempt}):", e)

        # now wait until the result span's text becomes non-empty and different from prev_text
        try:
            def result_has_text(driver):
                try:
                    el = driver.find_element(By.XPATH, RESULT_XPATH)
                    txt = el.text.strip()
                    if txt and txt != prev_text and txt.lower() not in ("n/a", "-", "--"):
                        return txt
                    return False
                except Exception:
                    return False

            # wait up to 8 seconds per attempt
            new_text = WebDriverWait(driver, 8, poll_frequency=0.4).until(result_has_text)
            raw_value = new_text if isinstance(new_text, str) else driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
            # CLEAN: remove currency symbols ₫ and đ (keep commas)
            if raw_value and raw_value.upper() not in ("N/A", "-", "--"):
                cleaned = raw_value.replace("₫", "").replace("đ", "").strip()
                cleaned = cleaned.replace(",", "")      # ← REMOVE COMMAS
                cleaned = re.sub(r'[\u00A0\s]+', '', cleaned) if cleaned else cleaned

                # If cleaned is empty after stripping, keep raw
                value = cleaned if cleaned else raw_value
            else:
                value = "N/A"

            print(f"[+] Got value on attempt {attempt}: {value}")
            break
        except Exception:
            print(f"[-] Attempt {attempt} failed to get value; retrying...")
            if attempt == max_attempts:
                try:
                    el = driver.find_element(By.XPATH, RESULT_XPATH)
                    print("Result outerHTML (debug):", el.get_attribute("outerHTML")[:800])
                except Exception as e:
                    print("Could not fetch result outerHTML:", e)
            time.sleep(0.6)

    results.append({
        "date": current.strftime("%Y-%m-%d"),
        "gold_price_vnd": value
    })

    # move to the 1st of next month
    current = add_one_month(current)
    time.sleep(0.4)

# ----------------------------------------------------
# SAVE CSV
# ----------------------------------------------------
df = pd.DataFrame(results)
df.to_csv("gold_prices_monthly.csv", index=False)

print("Saved: gold_prices_monthly.csv")

driver.quit()
