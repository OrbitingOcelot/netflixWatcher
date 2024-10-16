"""Module providing confirmation for Netflix Household update"""
import imaplib
import email
import re
import time
import os
import logging
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMAIL_IMAP = os.environ['EMAIL_IMAP']
EMAIL_LOGIN = os.environ['EMAIL_LOGIN']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']
EMAIL_POLLING_INTERVAL = int(os.environ['EMAIL_POLLING_INTERVAL'])
NETFLIX_EMAIL_SENDER = os.environ['NETFLIX_EMAIL_SENDER']



def extract_links(text):
    """Finds all https links"""
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, text)
    return urls


def open_link_with_selenium(body):
    """Opens Selenium and clicks a button to confirm connection"""
    message = "Link found, triggering access..."
    logger.info(message)

    links = extract_links(body)
    for link in links:
        if "update-primary-location" in link:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            driver = webdriver.Remote(
                command_executor='http://netflix_watcher_selenium:4444/wd/hub',
                options=options
            )

            driver.get(link)
            time.sleep(3)

            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.CSS_SELECTOR, '[data-uia="set-primary-location-action"]'
                    ))
                )

                element.click()
            except TimeoutException as exception:
                print("Error:", exception)

            time.sleep(3)
            driver.quit()


def fetch_last_unseen_email():
    """Gets body of last unseen mail from inbox"""
    mail = imaplib.IMAP4_SSL(EMAIL_IMAP)
    
    try:
        mail.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        mail.select("inbox")
    
        _, email_ids = mail.search(None, '(UNSEEN FROM ' + NETFLIX_EMAIL_SENDER + ')')
        email_ids = email_ids[0].split()
    
        if email_ids:
            email_id = email_ids[-1]
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
    
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if "text/plain" in content_type:
                        body = part.get_payload(decode=True).decode()
                        open_link_with_selenium(body)
            else:
                body = msg.get_payload(decode=True).decode()
                open_link_with_selenium(body)

    except Exception as e:
        message = f"IMAP Error: {e}"
        logger.error(message)

    finally:
        mail.logout()


if __name__ == "__main__":
    message = "Email monitoring starting"
    logger.info(message)
    while True:
        fetch_last_unseen_email()
        time.sleep(EMAIL_POLLING_INTERVAL)
