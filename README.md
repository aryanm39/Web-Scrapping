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

2. Set up the `.env` file with Firebase credentials.
3. Ensure `chromedriver` is installed for Selenium.
4. Run the script:
   ```bash
   python indiabix.py
   ```
