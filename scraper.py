from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime, timedelta
import time
import os

URL = "https://goldbroker.com/charts/gold-price/vnd?#historical-chart"

START_DATE = datetime(2022, 10, 1)
END_DATE   = datetime(2025, 10, 1)

CSV_FILE = "gold_prices_daily.csv"
# if file doesn't exist → create with header
if not os.path.isfile(CSV_FILE):
    df = pd.DataFrame(columns=["date", "gold_price_vnd"])
    df.to_csv(CSV_FILE, index=False)

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
driver.get(URL)

wait = WebDriverWait(driver, 20)

# ----------------------------------------------------
# STEP 1 — ACCEPT COOKIES
# ----------------------------------------------------
try:
    allow_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Allow all') or contains(.,'Allow All')]"))
    )
    allow_btn.click()
    print("[+] Cookie popup closed.")
except:
    print("[!] Cookie popup not found.")

time.sleep(1)

# ----------------------------------------------------
# STEP 2 — CLOSE AD POPUP
# ----------------------------------------------------
try:
    close_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]"))
    )
    close_btn.click()
    print("[+] Ad popup closed.")
except:
    print("[!] Ad popup not found.")

time.sleep(1)

# Scroll to form
driver.execute_script("window.scrollTo(0, 800);")
time.sleep(1)

# ----------------------------------------------------
# HELPERS
# ----------------------------------------------------
def close_ads_if_visible():
    try:
        close_btn = driver.find_element(By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]")
        if close_btn.is_displayed():
            driver.execute_script("arguments[0].click();", close_btn)
            print("[+] Ad popup closed inside loop.")
            time.sleep(0.5)
    except:
        pass

def wait_for_value(old_html="", timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        try:
            el = driver.find_element(By.XPATH, RESULT_XPATH)
            new_html = el.get_attribute("outerHTML")

            # Page updated (HTML changed)
            if new_html != old_html:
                txt = el.text.strip()
                if txt and txt.lower() not in ("n/a", "-", "--"):
                    return txt

        except:
            pass
        time.sleep(0.3)

    return None

def set_date_and_get_value(date_obj):
    date_str = date_obj.strftime("%d-%m-%Y")

    try:
        # Get old HTML BEFORE changing date
        try:
            old_html = driver.find_element(By.XPATH, RESULT_XPATH).get_attribute("outerHTML")
        except:
            old_html = ""

        # Refetch input each time
        date_input = wait.until(EC.element_to_be_clickable((By.XPATH, DATE_INPUT_XPATH)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
        driver.execute_script("arguments[0].value = '';", date_input)

        date_input.send_keys(date_str)
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """, date_input)

        # Click Get Value
        get_btn = wait.until(EC.element_to_be_clickable((By.XPATH, GET_BTN_XPATH)))
        driver.execute_script("arguments[0].click();", get_btn)

        # Wait for new value ONLY ONCE
        new_value = wait_for_value(old_html=old_html, timeout=8)

        if new_value:
            print(f"[+] Value updated: {new_value}")
            return new_value

        # If no update found → SKIP immediately
        print("[=] No update detected on first attempt — skipping this date.")
        return "SKIP"

    except Exception as e:
        print("[!] Failed to get value on first attempt:", e)
        return "SKIP"

RESULT_XPATH = "//*[@id='historical-chart']/section[3]/div/div/div/div/form/div[4]/span"
GET_BTN_XPATH = "//button[contains(.,'Get value') or contains(.,'Get Value') or contains(@class,'amcharts-period-input')]"
DATE_INPUT_XPATH = "//*[@id='form_xau_date']"

results = []

current = START_DATE
while current <= END_DATE:
    print("Processing:", current.strftime("%Y-%m-%d"))

    close_ads_if_visible()

    gold_value = set_date_and_get_value(current)
    
    # If no update → skip immediately
    if gold_value == "SKIP":
        current += timedelta(days=1)
        continue
    
    # append to CSV immediately
    pd.DataFrame([{
        "date": current.strftime("%Y-%m-%d"),
        "gold_price_vnd": gold_value
    }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

    print(f"[+] Saved row → {CSV_FILE}")

    current += timedelta(days=1)

