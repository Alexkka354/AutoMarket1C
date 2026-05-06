"""
Конфигурация модуля публикации на Авито.
Загружает креденшалы из файла .env.
"""

import os
from dotenv import load_dotenv

load_dotenv()

AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET")
