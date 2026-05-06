import asyncio
import json
import os
import subprocess
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
ONEC_PATH    = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
BASE_PATH    = r"C:\Users\bojce\Downloads\DemoEnterprise20"
LOGIN        = ""
PASSWORD     = ""
EXPORT_PATH  = r"C:\Users\bojce\Desktop\products.json"
EPF_PATH     = r"C:\Users\bojce\Desktop\adapter_1c\ExportProducts.epf"

def test_1_file_exists():
    """Тест 1 — проверяем что EPF файл существует"""
    print("\n" + "="*50)
    print("ТЕСТ 1: Проверка EPF файла")
    print("="*50)

    if os.path.exists(EPF_PATH):
        size = os.path.getsize(EPF_PATH)
        print(f"✅ Файл найден: {EPF_PATH}")
        print(f"   Размер: {size} байт")
        return True
    else:
        print(f"❌ Файл не найден: {EPF_PATH}")
        return False

def test_2_onec_exists():
    """Тест 2 — проверяем что 1С установлена"""
    print("\n" + "="*50)
    print("ТЕСТ 2: Проверка установки 1С")
    print("="*50)

    if os.path.exists(ONEC_PATH):
        print(f"✅ 1С найдена: {ONEC_PATH}")
        return True
    else:
        print(f"❌ 1С не найдена: {ONEC_PATH}")
        return False

def test_3_base_exists():
    """Тест 3 — проверяем что база 1С существует"""
    print("\n" + "="*50)
    print("ТЕСТ 3: Проверка базы 1С")
    print("="*50)

    if os.path.exists(BASE_PATH):
        print(f"✅ База найдена: {BASE_PATH}")
        return True
    else:
        print(f"❌ База не найдена: {BASE_PATH}")
        return False

def test_4_launch_1c():
    """Тест 4 — запускаем 1С и ждём выгрузки"""
    print("\n" + "="*50)
    print("ТЕСТ 4: Запуск 1С и выгрузка товаров")
    print("="*50)

    # Удаляем старый файл
    if os.path.exists(EXPORT_PATH):
        os.remove(EXPORT_PATH)
        print(f"🗑️  Удалён старый файл: {EXPORT_PATH}")

    # Команда запуска 1С
    command = [
        ONEC_PATH,
        "ENTERPRISE",
        "/F", BASE_PATH,
        "/N", LOGIN,
        "/P", PASSWORD,
        "/Execute", EPF_PATH,
        "/C", EXPORT_PATH,
        "/DisableStartupMessages",
        "/DisableStartupDialogs",
        "/NoSplash"
    ]

    print(f"🚀 Запускаем 1С...")
    print(f"   Команда: {' '.join(command)}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"   PID процесса: {process.pid}")

    # Ждём файл максимум 120 секунд
    print(f"\n⏳ Ожидаем файл выгрузки (до 120 сек)...")
    timeout = 120
    elapsed = 0

    while elapsed < timeout:
        time.sleep(3)
        elapsed += 3

        # Проверяем файл ошибки
        error_file = EXPORT_PATH + ".error.txt"
        if os.path.exists(error_file):
            with open(error_file, "r", encoding="utf-8") as f:
                error = f.read()
            os.remove(error_file)
            process.terminate()
            print(f"❌ 1С вернула ошибку:\n{error}")
            return False

        # Проверяем файл данных
        if os.path.exists(EXPORT_PATH):
            size = os.path.getsize(EXPORT_PATH)
            if size > 10:
                print(f"✅ Файл создан! ({size} байт, {elapsed} сек)")
                time.sleep(2)  # ждём завершения записи
                process.terminate()
                return True

        print(f"   Ждём... {elapsed} сек")

    process.terminate()
    print(f"❌ Таймаут — файл не появился за {timeout} секунд")
    return False

def test_5_read_json():
    """Тест 5 — читаем и проверяем JSON файл"""
    print("\n" + "="*50)
    print("ТЕСТ 5: Проверка содержимого файла")
    print("="*50)

    if not os.path.exists(EXPORT_PATH):
        print(f"❌ Файл не найден: {EXPORT_PATH}")
        return None

    try:
        with open(EXPORT_PATH, "r", encoding="utf-8") as f:
            products = json.load(f)

        print(f"✅ JSON прочитан успешно")
        print(f"   Количество товаров: {len(products)}")

        if len(products) == 0:
            print("⚠️  Список товаров пустой!")
            return products

        # Показываем первые 5 товаров
        print(f"\n📦 Первые 5 товаров:")
        for i, p in enumerate(products[:5]):
            print(f"\n  Товар {i+1}:")
            print(f"    Название: {p.get('name', 'н/д')}")
            print(f"    Артикул:  {p.get('article', 'н/д')}")
            print(f"    Остаток:  {p.get('stock', 0)} шт.")
            print(f"    Цена:     {p.get('price', 0)} руб.")

        return products

    except json.JSONDecodeError as e:
        print(f"❌ Ошибка чтения JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def test_6_validate_data(products):
    """Тест 6 — проверяем структуру данных"""
    print("\n" + "="*50)
    print("ТЕСТ 6: Валидация структуры данных")
    print("="*50)

    if not products:
        print("❌ Нет данных для валидации")
        return False

    required_fields = ["name", "article", "stock", "price"]
    errors = 0
    warnings = 0

    for i, product in enumerate(products):
        for field in required_fields:
            if field not in product:
                print(f"❌ Товар {i+1}: отсутствует поле '{field}'")
                errors += 1

        # Проверяем типы данных
        if not isinstance(product.get("stock", 0), (int, float)):
            print(f"⚠️  Товар {i+1}: поле 'stock' не число")
            warnings += 1

        if not isinstance(product.get("price", 0), (int, float)):
            print(f"⚠️  Товар {i+1}: поле 'price' не число")
            warnings += 1

    if errors == 0 and warnings == 0:
        print(f"✅ Все {len(products)} товаров прошли валидацию")
        return True
    else:
        print(f"\n⚠️  Ошибок: {errors}, Предупреждений: {warnings}")
        return errors == 0

def test_7_statistics(products):
    """Тест 7 — статистика выгруженных данных"""
    print("\n" + "="*50)
    print("ТЕСТ 7: Статистика данных")
    print("="*50)

    if not products:
        print("❌ Нет данных")
        return

    total = len(products)
    with_article = len([p for p in products
                        if p.get("article")])
    with_price   = len([p for p in products
                        if p.get("price", 0) > 0])
    with_stock   = len([p for p in products
                        if p.get("stock", 0) > 0])

    prices = [p.get("price", 0) for p in products
              if p.get("price", 0) > 0]
    avg_price = sum(prices) / len(prices) if prices else 0
    max_price = max(prices) if prices else 0
    min_price = min(prices) if prices else 0

    print(f"📊 Итоговая статистика:")
    print(f"   Всего товаров:       {total}")
    print(f"   С артикулом:         {with_article} ({with_article/total*100:.1f}%)")
    print(f"   С ценой > 0:         {with_price} ({with_price/total*100:.1f}%)")
    print(f"   С остатком > 0:      {with_stock} ({with_stock/total*100:.1f}%)")
    print(f"   Средняя цена:        {avg_price:.2f} руб.")
    print(f"   Максимальная цена:   {max_price:.2f} руб.")
    print(f"   Минимальная цена:    {min_price:.2f} руб.")

def run_all_tests():
    """Запускает все тесты последовательно"""
    print("\n" + "🔷"*25)
    print("ТЕСТИРОВАНИЕ АДАПТЕРА 1С")
    print("🔷"*25)

    results = {}

    # Тест 1 — EPF файл
    results["epf_exists"] = test_1_file_exists()

    # Тест 2 — 1С установлена
    results["onec_exists"] = test_2_onec_exists()

    # Тест 3 — База существует
    results["base_exists"] = test_3_base_exists()

    # Если базовые тесты прошли — запускаем 1С
    if all([results["epf_exists"],
            results["onec_exists"],
            results["base_exists"]]):

        # Тест 4 — Запуск 1С
        results["launch"] = test_4_launch_1c()

        if results["launch"]:
            # Тест 5 — Чтение JSON
            products = test_5_read_json()
            results["read_json"] = products is not None

            if products:
                # Тест 6 — Валидация
                results["validate"] = test_6_validate_data(products)

                # Тест 7 — Статистика
                test_7_statistics(products)
    else:
        print("\n❌ Базовые тесты не прошли — запуск 1С пропущен")

    # Итоговый результат
    print("\n" + "="*50)
    print("ИТОГ ТЕСТИРОВАНИЯ")
    print("="*50)
    passed = sum(1 for v in results.values() if v)
    total  = len(results)

    for test, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {test}")

    print(f"\nПройдено: {passed}/{total} тестов")

    if passed == total:
        print("\n🎉 Адаптер 1С работает корректно!")
        print("   Можно подключать интеграционный модуль.")
    else:
        print("\n⚠️  Есть проблемы — проверьте ошибки выше.")

if __name__ == "__main__":
    run_all_tests()