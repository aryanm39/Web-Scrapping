import os
import time
import json
import requests
import pandas as pd
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, db
import ast
from dotenv import load_dotenv
import socket

load_dotenv()
database_url = os.getenv("DATABASE_URL")
cred_json = os.getenv("CREDENTIALS_JSON")

if cred_json:
    try:
        cred_dict = json.loads(cred_json)
        try:
            firebase_admin.get_app()
            print("Firebase is already initialized, skipping re-initialization.")
        except ValueError:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            print("Firebase initialized successfully!")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in CREDENTIALS_JSON: {e}")
else:
    raise ValueError("CREDENTIALS_JSON not found in .env")

script_dir = os.path.dirname(os.path.abspath(__file__))
def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def scrape_indiabix(category, query, query_number, start_page, end_page):
    query_folder = os.path.join(script_dir, category, query)
    os.makedirs(query_folder, exist_ok=True)

    driver = webdriver.Chrome()
    file_index = 0

    for i in range(start_page, end_page + 1):
        while not is_internet_available():
            print("Internet disconnected. Retrying in 10 seconds...")
            time.sleep(10)

        try:
            if i <= 9:
                url = f"https://www.indiabix.com/{category}/{query}/{query_number}{i}"
            else:
                tens_place = i // 10
                i = i % 10 
                modified_query_number = f"{int(query_number) + tens_place:05d}"
                url = f"https://www.indiabix.com/{category}/{query}/{modified_query_number}{i}"
            
            driver.get(url)
            time.sleep(2)
            elems = driver.find_elements(By.CLASS_NAME, "bix-div-container")
            print(f"{len(elems)} items found on page {i}")

            for elem in elems:
                content = elem.get_attribute("outerHTML")
                file_path = os.path.join(query_folder, f"{file_index}.html")
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)
                file_index += 1

        except Exception as e:
            print(f"Error on page {i}: {e}. Retrying...")
            time.sleep(5)

    driver.quit()

def process_html_files(category, query):
    query_folder = os.path.join(script_dir, category, query)
    output_csv = os.path.join(query_folder, f"{query}.csv")
    data = []

    for root, _, files in os.walk(query_folder):
        for file in sorted(files, key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else float('inf')):
            if file.endswith(".html"):
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')

                        question = soup.find("div", class_="bix-td-qtxt")
                        question_text = question.get_text(strip=True) if question else "N/A"

                        options_div = soup.find("div", class_="bix-tbl-options")
                        options = [opt.get_text(strip=True) for opt in options_div.find_all("div", class_="bix-td-option-val")] if options_div else []

                        answer_input = soup.find("input", class_="jq-hdnakq")
                        answer = answer_input['value'] if answer_input else "N/A"

                        explanation_div = soup.find("div", class_="bix-ans-description")
                        explanation = explanation_div.get_text(strip=True) if explanation_div else "N/A"

                        data.append({
                            "question": question_text,
                            "options": options,
                            "answer": answer,
                            "explanation": explanation
                        })
                        print(f"Processed file: {file}")
                except Exception as e:
                    print(f"Error processing file {file}: {e}")

    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    print(f"Data saved to {output_csv}")
    return output_csv

def realtime_firebase(category, csv_path, query):
    db_path = f"Questions/{category}/{query}"
    ref = db.reference(db_path)

    log_file = f"{csv_path}.log"  # Log file to store last uploaded row index
    last_uploaded_index = 0
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            last_uploaded_index = int(f.read().strip())

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.DictReader(csvfile))

        for idx, row in enumerate(reader):
            if idx < last_uploaded_index:
                continue  # Skip already uploaded rows

            while not is_internet_available():
                print("Internet disconnected. Waiting to reconnect...")
                time.sleep(10)
            
            try:
                options_list = ast.literal_eval(row["options"]) if row["options"] else []
                
                question_data = {
                    "question": row["question"],
                    "options": options_list,
                    "answer": row["answer"],
                    "explanation": row["explanation"]
                }

                ref.push(question_data)
                print(f"Uploaded: {question_data}".replace("→", "->"))

                with open(log_file, "w") as f:
                    f.write(str(idx + 1))

            except Exception as e:
                print(f"Error uploading row {idx}: {row} - {e}")
                time.sleep(5)  # Retry delay
                break

if __name__ == "__main__":
    categories = ["Verbal-Reasoning", "Logical-Reasoning", "aptitude"]

    for category in categories:
        csv_file_path = os.path.join(script_dir, f"{category}.csv")

        if not os.path.exists(csv_file_path):
            print(f"CSV file for {category} not found. Skipping...")
            continue

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)

            for row in reader:
                if not any(row): 
                    print("Empty row encountered. Stopping execution.")
                    break
                if len(row) < 4:
                    print("Skipping row with insufficient arguments:", row)
                    continue

                query, query_number, start_page, end_page = row[:4]
                if not start_page.isdigit() or not end_page.isdigit():
                    print("Skipping row with non-numeric start_page or end_page:", row)
                    continue

                start_page, end_page = int(start_page), int(end_page)

                scrape_indiabix(category, query, query_number, start_page, end_page)
                csv_file = process_html_files(category, query)
                realtime_firebase(category, csv_file, query)
                print(f"Completed processing for category: {category}, query: {query}")
