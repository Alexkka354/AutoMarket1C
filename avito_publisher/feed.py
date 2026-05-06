"""
Генератор XML-фида в формате Авито Автозагрузки (formatVersion=3).

Формат фида:
    <?xml version="1.0" encoding="utf-8"?>
    <Ads formatVersion="3" target="Avito.ru">
        <Ad>
            <Id>уникальный_id</Id>
            <Title>Заголовок до 50 символов</Title>
            <Description>Описание товара</Description>
            <Price>10000</Price>
            <Category>Категория на Авито</Category>
            <Images>
                <Image url="https://..."/>
            </Images>
            ...
        </Ad>
    </Ads>

Документация Авито:
    https://developers.avito.ru/api-catalog/autoload/documentation
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Optional


def _prettify(elem: ET.Element) -> str:
    """Форматирует XML с отступами для читаемости."""
    raw = ET.tostring(elem, encoding="unicode")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def generate_feed(
    products: list[dict],
    manager_name: Optional[str] = None,
) -> str:
    """Генерирует XML-фид из списка товаров.

    Каждый товар (dict) может содержать поля:
        id            — уникальный ID объявления (обязательно)
        title         — заголовок (до 50 символов, обязательно)
        description   — описание (обязательно)
        price         — цена в рублях (обязательно)
        category      — категория на Авито (обязательно)
        image_urls    — список URL изображений (опционально)
        image_url     — URL одного изображения (опционально)
        address       — адрес продавца (опционально)
        contact_phone — телефон (опционально)
        condition     — состояние: "Новое" или "Б/у" (опционально)
        ad_status     — статус: "Free" или "TurboSale" и др. (по умолч. "Free")

    Возвращает строку с XML-документом.
    """
    ads = ET.Element("Ads", attrib={
        "formatVersion": "3",
        "target": "Avito.ru",
    })

    for product in products:
        ad = ET.SubElement(ads, "Ad")

        # --- Обязательные поля ---

        ad_id = str(product.get("id", ""))
        ET.SubElement(ad, "Id").text = ad_id

        ET.SubElement(ad, "DateBegin").text = (
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        )

        ad_status = product.get("ad_status", "Free")
        ET.SubElement(ad, "AdStatus").text = ad_status

        ET.SubElement(ad, "AllowEmail").text = "Да"

        category = product.get("category", "Товары для дома")
        ET.SubElement(ad, "Category").text = category

        title = product.get("title", "")
        if len(title) > 50:
            title = title[:50]
        ET.SubElement(ad, "Title").text = title

        description = product.get("description", "")
        ET.SubElement(ad, "Description").text = description

        price = product.get("price", 0)
        ET.SubElement(ad, "Price").text = str(int(price))

        # --- Изображения ---

        image_urls = product.get("image_urls", [])
        single_url = product.get("image_url")
        if single_url and not image_urls:
            image_urls = [single_url]

        if image_urls:
            images = ET.SubElement(ad, "Images")
            for url in image_urls:
                ET.SubElement(images, "Image", attrib={"url": url})

        # --- Опциональные поля ---

        address = product.get("address")
        if address:
            ET.SubElement(ad, "Address").text = address

        phone = product.get("contact_phone")
        if phone:
            ET.SubElement(ad, "ContactPhone").text = phone

        condition = product.get("condition")
        if condition:
            ET.SubElement(ad, "Condition").text = condition

        if manager_name:
            ET.SubElement(ad, "ManagerName").text = manager_name

    return _prettify(ads)


def save_feed(products: list[dict], filename: str = "avito_feed.xml", **kwargs) -> str:
    """Генерирует XML-фид и сохраняет в файл.

    Возвращает путь к файлу.
    """
    xml_content = generate_feed(products, **kwargs)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_content)
    return filename
