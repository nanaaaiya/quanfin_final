from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime, timedelta
import time
import os

URL = "https://goldbroker.com/charts/gold-price/vnd?#historical-chart"

START_DATE = datetime(2015, 10, 1)
END_DATE   = datetime(2025, 10, 1)

CSV_FILE = "gold_prices_f.csv"
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

def wait_for_new_value(old_value, timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        try:
            txt = driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
            if txt and txt != old_value and txt.lower() not in ("n/a", "-", "--"):
                return txt
        except:
            pass
        time.sleep(0.2)
    return None

def set_date_and_get_value(date_obj, max_attempts=5):
    date_str = date_obj.strftime("%d-%m-%Y")

    for attempt in range(max_attempts):
        try:
            # 1. Get old value BEFORE clicking anything
            try:
                old_value = driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
            except:
                old_value = ""

            # 2. Refetch date input every time
            date_input = wait.until(EC.element_to_be_clickable((By.XPATH, DATE_INPUT_XPATH)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
            driver.execute_script("arguments[0].value = '';", date_input)

            date_input.send_keys(date_str)
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
            """, date_input)

            # 3. Click Get value
            get_btn = wait.until(EC.element_to_be_clickable((By.XPATH, GET_BTN_XPATH)))
            driver.execute_script("arguments[0].click();", get_btn)

            # 4. Wait for result to UPDATE (not just appear)
            new_value = wait_for_new_value(old_value, timeout=15)

            if new_value:
                print(f"[+] New value: {new_value}")
                return new_value

            print(f"[-] Attempt {attempt+1}: result did not change.")

        except Exception as e:
            print(f"[-] Attempt {attempt+1} failed:", e)

        time.sleep(1)

    print(f"[!] Failed to get value for {date_str}")
    return "N/A"

RESULT_XPATH = "//*[@id='historical-chart']/section[3]/div/div/div/div/form/div[4]/span"
GET_BTN_XPATH = "//button[contains(.,'Get value') or contains(.,'Get Value') or contains(@class,'amcharts-period-input')]"
DATE_INPUT_XPATH = "//*[@id='form_xau_date']"

results = []

# ----------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------
# current = START_DATE

# while current <= END_DATE:
#     print("Processing:", current.strftime("%Y-%m-%d"))

#     close_ads_if_visible()

#     date_input = wait.until(EC.element_to_be_clickable((By.XPATH, DATE_INPUT_XPATH)))
#     driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
#     time.sleep(0.2)

#     driver.execute_script("arguments[0].value = '';", date_input)
#     time.sleep(0.05)

#     date_str = current.strftime("%d-%m-%Y")

#     try:
#         if not set_date_input(date_str):
#             print(f"[!] Failed to set date for {date_str}, skipping...")
#             current += timedelta(days=1)
#             continue
#     except:
#         driver.execute_script("arguments[0].value = arguments[1];", date_input, date_str)

#     driver.execute_script("""
#         arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
#         arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
#     """, date_input)

#     time.sleep(0.3)

#     prev_text = ""
#     try:
#         prev_text = driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
#     except:
#         prev_text = ""

#     value = "N/A"
#     max_attempts = 3

#     for attempt in range(1, max_attempts + 1):
#         close_ads_if_visible()

#         try:
#             get_btn = driver.find_element(By.XPATH, GET_BTN_XPATH)
#             driver.execute_script("arguments[0].click();", get_btn)
#         except Exception as e:
#             print(f"[!] Could not click Get value (attempt {attempt}):", e)

#         try:
#             def result_has_text(driver):
#                 try:
#                     txt = driver.find_element(By.XPATH, RESULT_XPATH).text.strip()
#                     if txt and txt.lower() not in ("n/a", "-", "--"):
#                         return txt
#                     return False
#                 except:
#                     return False

#             new_text = WebDriverWait(driver, 6, poll_frequency=0.4).until(result_has_text)
#             value = new_text
#             print(f"[+] Got value on attempt {attempt}: {value}")
#             break

#         except:
#             print(f"[-] Attempt {attempt} failed; retrying...")
#             time.sleep(0.6)

#     # --------------------------------------------------------
#     # SAVE ROW IMMEDIATELY (APPEND MODE)
#     # --------------------------------------------------------
#     df_row = pd.DataFrame([{
#         "date": current.strftime("%Y-%m-%d"),
#         "gold_price_vnd": value
#     }])

#     df_row.to_csv(
#         CSV_FILE,
#         mode="a",
#         header=False,   # IMPORTANT: do not write header again
#         index=False
#     )

#     print(f"[+] Saved row → {CSV_FILE}")

#     # next day
#     current += timedelta(days=1)

current = START_DATE
while current <= END_DATE:
    print("Processing:", current.strftime("%Y-%m-%d"))

    close_ads_if_visible()

    gold_value = set_date_and_get_value(current)
    
    # append to CSV immediately
    pd.DataFrame([{
        "date": current.strftime("%Y-%m-%d"),
        "gold_price_vnd": gold_value
    }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

    print(f"[+] Saved row → {CSV_FILE}")

    current += timedelta(days=1)

