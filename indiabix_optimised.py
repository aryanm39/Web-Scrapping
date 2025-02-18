import os
import time
import json
import requests
import pandas as pd
import csv
import logging
import ast
import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()
database_url = os.getenv("DATABASE_URL")
cred_json = os.getenv("CREDENTIALS_JSON")

if cred_json:
    try:
        cred_dict = json.loads(cred_json)
        try:
            firebase_admin.get_app()
            logging.info("Firebase is already initialized, skipping re-initialization.")
        except ValueError:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            logging.info("Firebase initialized successfully!")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in CREDENTIALS_JSON: {e}")
else:
    raise ValueError("CREDENTIALS_JSON not found in .env")

script_dir = Path(__file__).parent

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def scrape_indiabix(category, query, query_number, start_page, end_page):
    query_folder = script_dir / category / query
    query_folder.mkdir(parents=True, exist_ok=True)

    while not is_internet_available():
        logging.warning("Internet disconnected. Retrying in 10 seconds...")
        time.sleep(10)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    file_index = 0
    try:
        for i in range(start_page, end_page + 1):
            try:
                url = f"https://www.indiabix.com/{category}/{query}/{query_number}{i}" if i <= 9 else \
                      f"https://www.indiabix.com/{category}/{query}/{int(query_number) + (i // 10):05d}{i % 10}"
                
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "bix-div-container")))

                elems = driver.find_elements(By.CLASS_NAME, "bix-div-container")
                logging.info(f"{len(elems)} items found on page {i}")

                for elem in elems:
                    content = elem.get_attribute("outerHTML")
                    file_path = query_folder / f"{file_index}.html"
                    file_path.write_text(content, encoding="utf-8")
                    file_index += 1

            except Exception as e:
                logging.error(f"Error on page {i}: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    finally:
        driver.quit()

def process_single_file(file_path):
    try:
        soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), 'html.parser')

        question = soup.find("div", class_="bix-td-qtxt")
        question_text = question.get_text(strip=True) if question else "N/A"

        options_div = soup.find("div", class_="bix-tbl-options")
        options = [opt.get_text(strip=True) for opt in options_div.find_all("div", class_="bix-td-option-val")] if options_div else []

        if len(options) != 4:
            return None

        answer_input = soup.find("input", class_="jq-hdnakq")
        answer = answer_input['value'] if answer_input else "N/A"

        explanation_div = soup.find("div", class_="bix-ans-description")
        explanation = explanation_div.get_text(strip=True) if explanation_div else "N/A"

        return {"question": question_text, "options": options, "answer": answer, "explanation": explanation}
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return None

def process_html_files(category, query):
    query_folder = script_dir / category / query
    output_csv = query_folder / f"{query}.csv"

    files = [file for file in query_folder.iterdir() if file.suffix == ".html"]
    
    with ThreadPoolExecutor() as executor:
        data = list(filter(None, executor.map(process_single_file, files)))

    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    logging.info(f"Data saved to {output_csv}")
    return output_csv

def realtime_firebase(category, csv_path, query):
    db_path = f"Questions/{category}/{query}"
    ref = db.reference(db_path)

    log_file = csv_path.with_suffix(".log")
    last_uploaded_index = 0
    if log_file.exists():
        last_uploaded_index = int(log_file.read_text().strip())

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.DictReader(csvfile))

    batch = []
    for idx, row in enumerate(reader):
        if idx < last_uploaded_index:
            continue

        if not any(row.values()):
            logging.warning(f"Encountered an empty row at index {idx}. Stopping upload.")
            break

        options_list = ast.literal_eval(row["options"]) if row["options"] else []
        question_data = {
            "question": row["question"],
            "options": options_list,
            "answer": row["answer"],
            "explanation": row["explanation"]
        }
        ref.push(question_data)
        batch.append(question_data)

    if batch:
        logging.info(f"Uploaded {len(batch)} questions for {query} to Firebase.")
        log_file.write_text(str(last_uploaded_index + len(batch)))

if __name__ == "__main__":
    categories = ["aptitude", "Verbal-Reasoning", "Logical-Reasoning"]

    for category in categories:
        csv_file_path = script_dir / f"{category}.csv"

        if not csv_file_path.exists():
            logging.warning(f"CSV file for {category} not found. Skipping...")
            continue

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None) 

            for row in reader:
                if not any(row):
                    logging.warning("Empty row encountered. Stopping execution.")
                    break
                if len(row) < 4:
                    logging.warning(f"Skipping row with insufficient arguments: {row}")
                    continue

                query, query_number, start_page, end_page = row[:4]
                if not start_page.isdigit() or not end_page.isdigit():
                    logging.warning(f"Skipping row with non-numeric start_page or end_page: {row}")
                    continue

                start_page, end_page = int(start_page), int(end_page)

                scrape_indiabix(category, query, query_number, start_page, end_page)
                csv_file = process_html_files(category, query)
                realtime_firebase(category, csv_file, query)
                logging.info(f"Completed processing for category: {category}, query: {query}")
