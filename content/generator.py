from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from config import GIGACHAT_CLIENT_SECRET

async def generate_title(name: str, characteristics: str) -> str:
    with GigaChat(credentials=GIGACHAT_CLIENT_SECRET, verify_ssl_certs=False) as giga:
        response = giga.chat(Chat(
            messages=[Messages(
                role=MessagesRole.USER,
                content=f"Напиши только название товара без лишних слов, без слоганов, без восклицательных знаков, без markdown.\n"
                        f"Товар: {name}\n"
                        f"Пример правильного ответа: Смартфон Samsung Galaxy A54 8/256 ГБ чёрный\n"
                        f"Ответь только названием товара."
            )]
        ))
        return response.choices[0].message.content

async def generate_description(name: str, characteristics: str, platform: str) -> str:
    with GigaChat(credentials=GIGACHAT_CLIENT_SECRET, verify_ssl_certs=False) as giga:
        response = giga.chat(Chat(
            messages=[Messages(
                role=MessagesRole.USER,
                content=f"Создай продающее описание товара для площадки {platform}.\n"
                        f"Товар: {name}\n"
                        f"Характеристики: {characteristics}\n"
                        f"Требования: простой текст без markdown, без звёздочек, без решёток, "
                        f"без жирного шрифта, 3-5 предложений, выдели преимущества обычным текстом."
            )]
        ))
        return response.choices[0].message.content

async def classify_category(name: str, description: str) -> str:
    with GigaChat(credentials=GIGACHAT_CLIENT_SECRET, verify_ssl_certs=False) as giga:
        response = giga.chat(Chat(
            messages=[Messages(
                role=MessagesRole.USER,
                content=f"Определи категорию товара для площадки Авито.\n"
                        f"Товар: {name}\n"
                        f"Описание: {description}\n"
                        f"Ответь только названием категории, без пояснений, без markdown."
            )]
        ))
        return response.choices[0].message.content