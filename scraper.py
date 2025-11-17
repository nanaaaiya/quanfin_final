from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime, timedelta
import time

# Requirement: 
# Install the required packages using: pip install webdriver-manager selenium pandas

URL = "https://goldbroker.com/charts/gold-price/vnd?#historical-chart"

# format: YYYY, M, D
START_DATE = datetime(2023, 1, 1)
END_DATE   = datetime(2023, 1, 2)

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
except:
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
except:
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

def close_ads_if_visible():
    try:
        close_btn = driver.find_element(By.XPATH, "//button[contains(@class,'close') or contains(@aria-label,'Close')]")
        if close_btn.is_displayed():
            driver.execute_script("arguments[0].click();", close_btn)
            print("[+] Ad popup closed inside loop.")
            time.sleep(0.5)
    except:
        pass

current = START_DATE
while current <= END_DATE:

    print("Processing:", current.strftime("%Y-%m-%d"))

    # NEW: ad popups reappear randomly — close them
    close_ads_if_visible()

    # -----------------------------
    # Locate real date field
    # -----------------------------
    date_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='form_xau_date']"))
    )

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", date_input)
    time.sleep(0.2)

    # Clear using JS
    driver.execute_script("arguments[0].value = '';", date_input)
    time.sleep(0.1)

    # Type date
    date_input.send_keys(current.strftime("%d-%m-%Y"))

    # Dispatch events
    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
    """, date_input)

    time.sleep(0.4)

    # -----------------------------
    # Click "Get value"
    # -----------------------------
    get_btn = driver.find_element(By.XPATH, "//button[contains(.,'Get value')]")
    driver.execute_script("arguments[0].click();", get_btn)

    # -----------------------------
    # Extract result
    # -----------------------------
    try:
        result = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class,'value')]")
            )
        )
        value = result.text.strip()
    except:
        value = "N/A"

    results.append({
        "date": current.strftime("%Y-%m-%d"),
        "gold_price_vnd": value
    })

    current += timedelta(days=1)
    time.sleep(0.3)

# ----------------------------------------------------
# SAVE CSV
# ----------------------------------------------------
df = pd.DataFrame(results)
df.to_csv("gold_prices.csv", index=False)

print("Saved: gold_prices.csv")

driver.quit()
