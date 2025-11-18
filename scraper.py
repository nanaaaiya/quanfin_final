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
START_DATE = datetime(2016, 5, 10)
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
    # set the date with JS too (sometimes send_keys still blocked)
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
    # get the element reference for the result (may exist but be empty)
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

                    # Accept ANY valid number (weekend same as Friday)
                    if txt and txt.lower() not in ("n/a", "-", "--"):
                        return txt

                    return False
                except Exception:
                    return False

            # wait up to 6 seconds per attempt
            new_text = WebDriverWait(driver, 6, poll_frequency=0.4).until(result_has_text)
            value = new_text if isinstance(new_text, str) else driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
            print(f"[+] Got value on attempt {attempt}: {value}")
            break
        except Exception:
            print(f"[-] Attempt {attempt} failed to get value; retrying...")
            # for debugging, print outerHTML of result area if last attempt
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

    current += timedelta(days=1)
    time.sleep(0.4)

# ----------------------------------------------------
# SAVE CSV
# ----------------------------------------------------
    df = pd.DataFrame(results)
    df.to_csv("gold_prices1.csv", index=False)

# print("Saved: gold_prices.csv")

driver.quit()
