import os
import logging

TOKEN = '7715903410:AAFp2X33NnsID77tX-rjwcYSKqBx3fXIRTk'

CHANNELS = [
    {"username": "qadriyatmatematika", "url": "https://t.me/qadriyatmatematika"},
    {"username": "qadriyatmatematikachat", "url": "https://t.me/qadriyatmatematikachat"},
    {"username": "qadriyateducation", "url": "https://t.me/qadriyateducation"},
]

ADMIN_USERNAMES = ["maths_diyorbek", "ablaze_coder", "UmidullayevEldor"]
DATABASE_URL = "postgresql://dtmtest_user:uUXJI6NnJy7g5HxkArrJL7WfZoHxXulH@dpg-ctba6e68ii6s73fvg0eg-a.oregon-postgres.render.com/dtmtest"
ADMIN_IDS = [6236467772, 6943890915, 5864500255]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

