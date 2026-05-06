import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Optional


def _prettify(elem: ET.Element) -> str:
    """Форматирует XML с отступами для читаемости."""
    raw = ET.tostring(elem, encoding="unicode")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def generate_feed(products: list[dict], manager_name: Optional[str] = None) -> str:
    """Генерирует XML-фид в формате Авито Автозагрузки.

    Каждый товар (dict) должен содержать:
      - id / article  — уникальный идентификатор (Id)
      - name          — заголовок объявления (Title)
      - description   — описание (Description)
      - price         — цена (Price)
      - category      — категория на Авито (Category)
      - image_url     — ссылка на главное изображение (Images/Image)
      - address       — адрес продавца (Address, опционально)
      - contact_phone — телефон (ContactPhone, опционально)

    Возвращает строку с XML-документом.
    """
    ads = ET.Element("Ads", attrib={
        "formatVersion": "3",
        "target": "Avito.ru",
    })

    for product in products:
        ad = ET.SubElement(ads, "Ad")

        ad_id = str(product.get("article") or product.get("id", ""))
        ET.SubElement(ad, "Id").text = ad_id
        ET.SubElement(ad, "DateBegin").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(ad, "AdStatus").text = "Free"
        ET.SubElement(ad, "AllowEmail").text = "Да"

        category = product.get("category") or "Товары для дома"
        ET.SubElement(ad, "Category").text = category

        title = product.get("name", "")
        if len(title) > 50:
            title = title[:50]
        ET.SubElement(ad, "Title").text = title

        description = product.get("description") or product.get("name", "")
        ET.SubElement(ad, "Description").text = description

        price = product.get("price", 0)
        ET.SubElement(ad, "Price").text = str(int(price))

        image_url = product.get("image_url")
        if image_url:
            images = ET.SubElement(ad, "Images")
            ET.SubElement(images, "Image", attrib={"url": image_url})

        address = product.get("address")
        if address:
            ET.SubElement(ad, "Address").text = address

        phone = product.get("contact_phone")
        if phone:
            ET.SubElement(ad, "ContactPhone").text = phone

        if manager_name:
            ET.SubElement(ad, "ManagerName").text = manager_name

        stock = product.get("stock", 0)
        if stock and stock > 0:
            ET.SubElement(ad, "Condition").text = "Новое"

    return _prettify(ads)


def generate_single_ad_feed(
    ad_id: str,
    title: str,
    description: str,
    price: float,
    category: str = "Товары для дома",
    image_url: Optional[str] = None,
    address: Optional[str] = None,
    contact_phone: Optional[str] = None,
) -> str:
    """Генерирует XML-фид для одного объявления."""
    product = {
        "article": ad_id,
        "name": title,
        "description": description,
        "price": price,
        "category": category,
        "image_url": image_url,
        "address": address,
        "contact_phone": contact_phone,
    }
    return generate_feed([product])
