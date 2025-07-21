from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import os

# Chrome options
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
options.add_argument("--disable-infobars")
options.add_argument("--lang=en-US")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

# Initialize WebDriver
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

def scroll_to_bottom():
    """Scroll to the bottom of the page to load all models"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_models():
    return WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.bg-primary-bg.cursor-pointer.sm\\:shadow-md")
        )
    )

def main():
    results = []
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"cashify_prices_with_ram_{timestamp}.xlsx"
    main_url = "https://www.cashify.in/sell-old-mobile-phone/sell-apple"

    try:
        driver.get(main_url)
        time.sleep(3)
        scroll_to_bottom()

        models = get_models()
        print(f"Found {len(models)} models")

        for index in range(len(models)):
            try:
                models = get_models()
                if index >= len(models):
                    continue

                model = models[index]
                model_name = model.find_element(By.CSS_SELECTOR, "span.inherit").text.strip()
                print(f"\nProcessing model {index + 1}/{len(models)}: {model_name}")

                # Click the model
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", model)
                time.sleep(1)
                model.click()
                time.sleep(2)

                try:
                    # Extract RAM + Storage from variant blocks
                    variant_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "div.bg-primary-bg.cursor-pointer.p-3.shadow-md")
                        )
                    )

                    variant_infos = []
                    for v in variant_elements:
                        full_text = v.find_element(By.TAG_NAME, "h6").text.strip()
                        if '/' in full_text:
                            ram, storage = full_text.split('/')
                            variant_infos.append((ram.strip(), storage.strip()))
                        else:
                            variant_infos.append(("", full_text.strip()))

                    print(f"Found {len(variant_infos)} variants: {variant_infos}")

                    for ram_info, storage_info in variant_infos:
                        try:
                            # Re-locate variants
                            variant_buttons = driver.find_elements(By.CSS_SELECTOR, "div.bg-primary-bg.cursor-pointer.p-3.shadow-md")
                            for variant in variant_buttons:
                                full_text = variant.find_element(By.TAG_NAME, "h6").text.strip()
                                if ram_info and storage_info:
                                    match = f"{ram_info} / {storage_info}"
                                else:
                                    match = storage_info

                                if full_text.strip() == match:
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", variant)
                                    driver.execute_script("arguments[0].click();", variant)
                                    print(f"Selected variant: {match}")
                                    time.sleep(2)

                                    try:
                                        price_element = WebDriverWait(driver, 5).until(
                                            EC.visibility_of_element_located(
                                                (By.CSS_SELECTOR, "span.extraFont1.text-error")
                                            )
                                        )
                                        price = price_element.text
                                        print(f"Price found: {price}")
                                    except:
                                        price = "Price not available"
                                        print(f"Price not found for: {match}")

                                    results.append({
                                        "Model": model_name,
                                        "RAM": ram_info,
                                        "Storage": storage_info,
                                        "Price": price
                                    })
                                    break

                            # Go back to variant selection page
                            driver.back()
                            time.sleep(2)

                        except Exception as e:
                            print(f"Error processing variant {ram_info} / {storage_info}: {str(e)}")
                            results.append({
                                "Model": model_name,
                                "RAM": ram_info,
                                "Storage": storage_info,
                                "Price": "Error"
                            })

                except (TimeoutException, NoSuchElementException):
                    print("No variants found, checking single price")
                    try:
                        price_element = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.CSS_SELECTOR, "span.extraFont1.text-error")
                            )
                        )
                        price = price_element.text
                        print(f"Price found: {price}")
                    except:
                        price = "Price not available"

                    results.append({
                        "Model": model_name,
                        "RAM": "",
                        "Storage": "No Variant",
                        "Price": price
                    })

            except Exception as e:
                print(f"Error processing model: {str(e)}")
                results.append({
                    "Model": f"Error at index {index}",
                    "RAM": "N/A",
                    "Storage": "N/A",
                    "Price": "N/A"
                })

            finally:
                driver.get(main_url)
                time.sleep(2)
                scroll_to_bottom()

        # Save final data
        df = pd.DataFrame(results)
        df.to_excel(output_file, index=False)
        print(f"\n✅ Results saved to: {os.path.abspath(output_file)}")
        print(f"📦 Total records: {len(results)}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
