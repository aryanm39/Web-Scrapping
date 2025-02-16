# Indiabix Web Scraper

## Description
This Python script scrapes questions from Indiabix, processes the extracted HTML files into structured data, and uploads them to Firebase Realtime Database.

## Features
- Scrapes questions from Indiabix based on category and query.
- Processes and extracts relevant question data (question, options, answer, explanation).
- Saves extracted data as CSV files.
- Uploads structured data to Firebase Realtime Database.
- Handles internet disconnection gracefully.
- Uses multithreading for faster processing.

## Requirements
### Python Libraries
Ensure you have the following libraries installed:

```bash
pip install requests pandas selenium beautifulsoup4 firebase-admin python-dotenv
```

### Environment Variables (.env file)
Create a `.env` file and include:

```
DATABASE_URL=<your_firebase_database_url>
CREDENTIALS_JSON=<your_firebase_credentials_json>
```

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up the `.env` file with Firebase credentials.
3. Ensure `chromedriver` is installed for Selenium.
4. Run the script:
   ```bash
   python test.py
   ```

## Usage
### Functionality
- **Scrape Questions:**
  ```python
  scrape_indiabix(category, query, query_number, start_page, end_page)
  ```
  Scrapes questions from Indiabix for the specified category and range.

- **Process HTML Files:**
  ```python
  process_html_files(category, query)
  ```
  Converts extracted HTML files into structured CSV format.

- **Upload to Firebase:**
  ```python
  realtime_firebase(category, csv_path, query)
  ```
  Uploads processed data to Firebase Realtime Database.

## Logging
The script uses Python's `logging` module to log warnings, errors, and progress updates.

## File Structure
```
├── test.py
├── .env
├── requirements.txt
├── data/
│   ├── <category>/<query>/
│   │   ├── 0.html
│   │   ├── 1.html
│   │   ├── query.csv
│   │   ├── query.log
```

## Notes
- Ensure a stable internet connection while scraping.
- The script automatically retries when an internet issue is detected.
- Firebase credentials should be securely managed.
