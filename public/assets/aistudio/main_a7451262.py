import asyncio
import json
from playwright.async_api import async_playwright


async def search_court_docs_filtered():
    async with async_playwright() as p:
        # Открываем браузер с интерфейсом
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()

        print("🌐 Переходим на страницу поиска документов...")
        await page.goto("https://www.vsrf.ru/documents", wait_until="networkidle")

        keyword = "автомобиль"
        print(f"⌨️ Вводим поисковый запрос: '{keyword}'")

        input_selector = "input#documents-form-keyword"
        await page.wait_for_selector(input_selector, timeout=10000)

        await page.click(input_selector)
        await page.type(input_selector, keyword, delay=100)

        # Устанавливаем фильтр по последним 3 годам (2024, 2025, 2026)
        print("📅 Устанавливаем фильтр по годам (2024, 2025, 2026)...")
        for year in ["2021", "2022", "2023", "2024", "2025", "2026"]:
            checkbox_selector = f"button#checkbox-{year}"
            try:
                checkbox = page.locator(checkbox_selector)
                if await checkbox.count() > 0:
                    is_checked = await checkbox.get_attribute("aria-checked")
                    if is_checked == "false":
                        await checkbox.click()
                        await page.wait_for_timeout(500)
            except Exception as e:
                print(f"⚠️ Не удалось выбрать год {year}: {e}")

        # Отправляем форму поиска
        submit_btn_selector = "button[type='submit'][form='documents-form']"
        print("🔍 Отправляем форму поиска...")
        await page.click(submit_btn_selector)

        # Ждем загрузки первичных результатов
        print("⏳ Ждем загрузки результатов...")
        await page.wait_for_timeout(5000)

        # Нажимаем кнопку «Показать ещё» до упора (используем .first, чтобы избежать strict mode error)
        print("🔄 Проверяем наличие кнопки подгрузки дополнительных результатов...")
        while True:
            try:
                load_more_btn = page.locator("button:has-text('Показать ещё'), button:has-text('Загрузить ещё')").first
                if await load_more_btn.count() > 0 and await load_more_btn.is_visible():
                    print("👇 Нажимаем «Показать ещё»...")
                    await load_more_btn.click()
                    await page.wait_for_timeout(3000)
                else:
                    print("✅ Все страницы успешно развернуты.")
                    break
            except Exception as e:
                print(f"ℹ️ Больше нет страниц для подгрузки или кнопка недоступна: {e}")
                break

        # СОБИРАЕМ ССЫЛКИ С СУЖДЕНИЯМИ И ДОКУМЕНТАМИ
        links = await page.locator("a[href]").all()
        print(f"\n🔍 Всего найдено тегов <a> на странице: {len(links)}")

        extracted_docs = []
        for link in links:
            href = await link.get_attribute("href")
            title = await link.inner_text()

            if href and title:
                clean_title = title.strip().replace("\n", " ")

                # ЖЕСТКИЙ ФИЛЬТР: оставляем только ссылки на файлы документов (PDF / media-proxy)
                # И исключаем внешние сайты (kremlin.ru, sudrf.ru и т.д.) и служебные разделы
                is_document = ("/media-proxy/" in href or href.lower().endswith(".pdf"))
                is_external = any(ext in href for ext in
                                  ["kremlin.ru", "ksrf.ru", "sudrf.ru", "arbitr.ru", "cdep.ru", "rgup.ru", "gov.ru",
                                   "vk.com", "youtube.com", "rutube.ru"])
                is_service = any(
                    skip in href for skip in ["/lk", "/contacts", "/press-center", "/about/", "/additional/"])

                if is_document and not is_external and not is_service and len(clean_title) > 10:
                    full_url = f"https://www.vsrf.ru{href}" if href.startswith("/") else href
                    extracted_docs.append({
                        "title": clean_title,
                        "url": full_url
                    })

        # Убираем дубликаты по URL
        unique_docs = list({doc['url']: doc for doc in extracted_docs}.values())

        print(f"\n[SUCCESS] Отфильтровано реальных документов: {len(unique_docs)}\n" + "=" * 50)

        for idx, doc in enumerate(unique_docs[:15], 1):
            print(f"{idx}. 📌 Заголовок: {doc['title']}")
            print(f"   🔗 Ссылка:    {doc['url']}")
            print("-" * 50)

        # Сохраняем в JSON
        with open("vsrf_court_docs.json", "w", encoding="utf-8") as f:
            json.dump(unique_docs, f, ensure_ascii=False, indent=4)
        print("💾 Данные сохранены в файл: vsrf_court_docs.json")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(search_court_docs_filtered())