from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import os
import uuid
import requests
from datetime import datetime
from pymongo import MongoClient
from bs4 import BeautifulSoup
import time
import json

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = "twitter_trending"
COLLECTION_NAME = "trending_topics"

# ProxyMesh Configuration
PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = os.getenv('PROXY_PORT')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
proxy_url = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

# Flask app setup
app = Flask(__name__)

# Environment variables for Twitter credentials
TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')

class TwitterScraper:
    def __init__(self, driver):
        self.driver = driver

    def wait_for_element(self, by, value, timeout=10):
        try:
            return self.driver.find_element(by, value)
        except Exception as e:
            print(f"Error waiting for element {value}: {e}")
        return None

    def login_and_fetch_trending_topics(self):
        """Login to Twitter and fetch trending topics."""
        self.driver.get("https://x.com/i/flow/login")
        time.sleep(3)

        username_input = self.wait_for_element(By.CSS_SELECTOR, 'input[autocomplete="username"]')
        if username_input:
            username_input.send_keys(TWITTER_USERNAME, Keys.RETURN)

        time.sleep(3)
        password_input = self.wait_for_element(By.CSS_SELECTOR, 'input[name="password"]')
        if password_input:
            password_input.send_keys(TWITTER_PASSWORD, Keys.RETURN)

        time.sleep(5)
        self.driver.get("https://x.com/explore/tabs/trending")
        time.sleep(5)

        trending_data = self.get_trending_topics()
        ip_used = requests.get("https://api.ipify.org").text

        # MongoDB storage logic
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        record_id = str(uuid.uuid4())
        record = {
            "_id": record_id,
            "trend1": trending_data[0] if len(trending_data) > 0 else "",
            "trend2": trending_data[1] if len(trending_data) > 1 else "",
            "trend3": trending_data[2] if len(trending_data) > 2 else "",
            "trend4": trending_data[3] if len(trending_data) > 3 else "",
            "trend5": trending_data[4] if len(trending_data) > 4 else "",
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip_used
        }

        collection.insert_one(record)
        self.driver.quit()

        return trending_data, ip_used, record

    def get_trending_topics(self):
        """Fetch trending topics using BeautifulSoup."""
        page_html = self.driver.page_source
        soup = BeautifulSoup(page_html, "html.parser")
        trends = soup.find_all("div", {"data-testid": "trend"}, limit=5)

        trending_data = []
        for trend in trends:
            try:
                topic_name = trend.find('div', class_='css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-b88u0q r-1bymd8e')
                if topic_name:
                    trending_data.append(topic_name.get_text(strip=True))
            except Exception as e:
                continue
        return trending_data

@app.route('/')
def home():
    """Display the main page with a button to run the script."""
    return render_template('index.html')

@app.route('/run_scraper', methods=['POST'])
def run_scraper():
    """Trigger the Twitter scraping and return results in an HTML page."""
    driver = webdriver.Chrome(service=Service("C:\\webdrivers\\chromedriver.exe"))
    scraper = TwitterScraper(driver)

    try:
        trending_data, ip_used, record = scraper.login_and_fetch_trending_topics()
        record["timestamp"] = record["timestamp"]  # Make sure datetime is string
        return render_template('results.html', trending_data=trending_data, ip_used=ip_used, record=record)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Something went wrong while scraping the data."})

if __name__ == '__main__':
    app.run(debug=True)
