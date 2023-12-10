import json
import math
import time
from python_pushover_open_client import PushoverOpenClientRealTime
from python_pushover_open_client import PushoverOpenClient
from python_pushover_open_client import CREDENTIALS_FILENAME
from python_pushover_open_client import register_parser
from kasa import SmartPlug
import logging
import asyncio
from threading import Thread

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logging.info("Starting lamp-website-notification server...")

LAMP_IP_ADDR: str = "10.0.0.53"
LAMP_ON_DURATION: int = 30  # seconds


def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def setup_background_loop():
    loop = asyncio.new_event_loop()
    t = Thread(target=start_background_loop, args=(loop,), daemon=True)
    t.start()
    return loop


pushover_credentials = json.load(open(CREDENTIALS_FILENAME))
lamp = SmartPlug(LAMP_IP_ADDR)
background_loop = setup_background_loop()
turn_off_after_task = None
turn_on_time = None


def setup_pushover():
    pushover_open_client = PushoverOpenClient()
    pushover_open_client.login()
    pushover_open_client.register_device()
    pushover_open_client.download_messages()
    pushover_open_client.delete_all_messages()


async def turn_on():
    global lamp
    global turn_on_time
    await lamp.update()
    if lamp.is_off:
        logging.info(f"Turn ON lamp")
        await lamp.turn_on()
        turn_on_time = time.time()
    else:
        logging.info("The lamp is already ON")


async def turn_off_after(seconds: int):
    global lamp
    global turn_on_time
    logging.info(f"Schedule turn OFF in {seconds} seconds")
    await asyncio.sleep(seconds)
    lamp_on_time = int(math.ceil(time.time() - turn_on_time))
    logging.info(f"Turn OFF lamp. It was on for {lamp_on_time} seconds")
    await lamp.turn_off()
    logging.info("")


@register_parser
def personal_website_send_parser(raw_data=None):
    global background_loop
    global turn_off_after_task
    if raw_data["message"].find("New personal website visit") != -1 and \
            raw_data["app"] == "Personal Website":
        logging.info("New personal website visit!")
        asyncio.run_coroutine_threadsafe(turn_on(), background_loop)
        if turn_off_after_task is not None and not turn_off_after_task.done():
            logging.info("Cancel turn OFF task")
            turn_off_after_task.cancel()
        turn_off_after_task = asyncio.run_coroutine_threadsafe(
            turn_off_after(LAMP_ON_DURATION), background_loop)


if "device_id" not in pushover_credentials or \
        "secret" not in pushover_credentials:
    logging.info(
        f"The \"device_id\" and \"secret\" were not found in {CREDENTIALS_FILENAME}. Setting up a new pushover device...")
    setup_pushover()
    logging.info("Done!")

client = PushoverOpenClientRealTime()
client.run_forever()
