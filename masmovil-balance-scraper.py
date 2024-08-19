import re
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
import time
import paho.mqtt.client as mqtt
import os
import json

load_dotenv()
masmovil_phone = os.getenv('MASMOVIL_NUMBER')
mqtt_user = os.getenv('MQTT_USER')
mqtt_password = os.getenv('MQTT_PASSWORD')
mqtt_server = os.getenv('MQTT_BROKER')
mqtt_port = int(os.getenv('MQTT_PORT'))
mqtt_topic = os.getenv('MASMOVIL_MQTT_TOPIC')
mqtt_error_topic = os.getenv('MASMOVIL_MQTT_ERROR_TOPIC')  # Separate Topic for errors

def run(playwright: Playwright) -> None:

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://pagoexpress.masmovilpanama.com/paybill")

    try:
        page.locator("#mat-radio-3 div").click()
        page.get_by_role("button", name="Continuar").click()
        page.locator("#care-app").press("Tab")
        page.get_by_placeholder("-0000").fill("6400-1125")
        page.get_by_role("button", name="Pagar este número").click()

        # Getting balance
        #balance_element = page.query_selector('//*[@id="mat-radio-11"]/label/span[2]/div/div[1]/p[1]')
        balance_element = page.inner_html('//*[@id="mat-radio-7"]/label/span[2]/div/div[1]/p[1]/span')
        if balance_element is None:
            raise ValueError("Element for balance not found.")
        
        #balance = balance_element.text_content()
        balance = balance_element.replace("B/. ", "")
        print(balance)
    except (TimeoutError, ValueError) as e:
        error_message = f"Error getting balance: {str(e)}"
        print(error_message)
        send_mqtt_error(mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_error_topic, error_message)
        balance = "Error"
    finally:
        context.close()
        browser.close()

    send_mqtt_data(mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_topic, balance)

def send_mqtt_data(server, port, user, password, topic, balance):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, mqtt_user)
    client.username_pw_set(user, password)
    client.connect(server, port)
    client.loop_start()
    
    xpayload = json.dumps({
        "state": str(balance),
        "updated_ts": str(int(time.time())),
        "updated_dt": str(datetime.now())
    }, sort_keys=True, default=str)
    
    client.publish(topic=topic, payload=xpayload, qos=0, retain=False)
    time.sleep(1)
    client.loop_stop()

def send_mqtt_error(server, port, user, password, topic, error_message):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, mqtt_user)
    client.username_pw_set(user, password)
    client.connect(server, port)
    client.loop_start()
    
    xpayload = json.dumps({
        "error": error_message,
        "updated_ts": str(int(time.time())),
        "updated_dt": str(datetime.now())
    }, sort_keys=True, default=str)
    
    client.publish(topic=topic, payload=xpayload, qos=0, retain=False)
    time.sleep(1)
    client.loop_stop()

with sync_playwright() as playwright:
    run(playwright)