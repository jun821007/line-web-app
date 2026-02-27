#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盤商每日價格爬蟲 - 截圖 → Gemini 識別 → 寫入 Google 試算表
試算表: 10b-8mfcjpTvuAT8MBxbvOEe9q6_LRXUwSlJeZI13_0E
分頁: 新機總表 / 整理後報表
"""

import os
import sys
import json
import time
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# ========== 設定 ==========
SPREADSHEET_ID = "10b-8mfcjpTvuAT8MBxbvOEe9q6_LRXUwSlJeZI13_0E"
WORKSHEET_NAME = "新機總表"
SUMMARY_WORKSHEET_NAME = "整理後報表"
HEADERS = ["盤商", "盤商網頁", "型號", "顏色", "價格", "最後更新時間"]

DEFAULT_TARGET_URLS = [
    {"name": "範例盤商", "url": "https://example.com/price-list"},
]

GEMINI_MODEL = "gemini-2.5-flash"

INVALID_PRICE_KEYWORDS = {"call", "洽詢", "詢", "洽", "電洽", "來電", ""}


def get_target_urls():
    raw = os.environ.get("TARGET_URLS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return DEFAULT_TARGET_URLS


def get_gspread_client():
    creds_json = os.environ.get("GSPREAD_CREDENTIALS_JSON")
    key_file = os.environ.get("GSPREAD_KEY_FILE", "gspread_key.json")

    if creds_json:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(creds_json)
            path = f.name
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(path, scopes=scope)
            return gspread.authorize(creds)
        finally:
            os.unlink(path)
    if os.path.exists(key_file):
        return gspread.service_account(filename=key_file)
    raise FileNotFoundError(
        "請設定 GSPREAD_CREDENTIALS_JSON 環境變數，或放置 gspread_key.json"
    )


def init_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("請設定 GEMINI_API_KEY 環境變數")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def create_chrome_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    if os.environ.get("GITHUB_ACTIONS"):
        opts.binary_location = "/usr/bin/google-chrome"
    return webdriver.Chrome(options=opts)


def capture_full_page_screenshots(driver, url, viewport_height=900, scroll_pause=1.5, max_screenshots=20):
    driver.get(url)
    driver.implicitly_wait(5)
    time.sleep(2)

    total_height = driver.execute_script(
        "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
    )

    screenshots = []
    current_position = 0

    while current_position < total_height and len(screenshots) < max_screenshots:
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(scroll_pause)
        png = driver.get_screenshot_as_png()
        screenshots.append(png)
        current_position += viewport_height

    if len(screenshots) < max_screenshots:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        screenshots.append(driver.get_screenshot_as_png())

    return screenshots


def extract_prices_from_image(model, image_bytes, source_name, source_url):
    prompt = """這是一張盤商報價單截圖。請從圖片中辨識「型號」、「顏色」與「價格」。
規則：
1. 顏色若有請填入，若報價單中該欄無顏色資訊則填空字串。
2. 若該商品文字顏色明顯較淺（灰色、半透明、淡色），代表缺貨，請略過不要回傳。
3. 只回傳有貨（文字清晰、顏色正常）的商品。
4. 價格欄位若為「call」、「洽詢」、「電洽」、空白或無法辨識為數字，請略過不要回傳。
5. price 欄位必須是整數數字，不可為字串。
回傳格式必須是 JSON 陣列，每個元素為 {"model": "型號", "color": "顏色", "price": 數字}。
範例: [{"model": "iPhone 17 Pro 256G", "color": "藍色", "price": 37500}]
若無法辨識或圖中無報價，回傳 []。只回傳 JSON，不要其他說明。"""

    img_part = {"mime_type": "image/png", "data": image_bytes}
    try:
        response = model.generate_content([prompt, img_part])
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        if not isinstance(data, list):
            return []
        rows = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in data:
            m = item.get("model") or item.get("型號") or ""
            c = item.get("color") or item.get("顏色") or ""
            p = item.get("price") or item.get("價格") or 0

            if isinstance(p, str):
                if p.strip().lower() in INVALID_PRICE_KEYWORDS:
                    continue
            try:
                p = int(float(str(p).replace(",", "")))
            except (TypeError, ValueError):
                continue

            if p <= 0:
                continue

            if m:
                rows.append([source_name, source_url, str(m), str(c), p, now])
        return rows
    except Exception as e:
        print(f"  [Gemini] 辨識失敗: {e}")
        return []


def deduplicate_rows(rows):
    seen = set()
    result = []
    for row in rows:
        key = (row[0], row[2], row[3], row[4])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def ensure_headers(ws):
    row1 = ws.row_values(1)
    if row1 != HEADERS:
        ws.update("A1:F1", [HEADERS])


def build_summary(sh, all_rows):
    """
    將原始資料整理成 pivot 報表，寫入「整理後報表」分頁。
    欄位：型號 | 顏色 | 盤商A | 盤商B | ... | 最低價 | 最低盤商 | 更新時間
    同型號＋顏色合併為同一列。
    """
    if not all_rows:
        return

    dealers = []
    for row in all_rows:
        d = row[0]
        if d not in dealers:
            dealers.append(d)

    pivot = {}
    update_time = ""
    for row in all_rows:
        dealer, _, model, color, price, ts = row[0], row[1], row[2], row[3], row[4], row[5]
        key = (model, color)
        if key not in pivot:
            pivot[key] = {}
        if dealer not in pivot[key] or price < pivot[key][dealer]:
            pivot[key][dealer] = price
        if not update_time and ts:
            update_time = ts

    header = ["型號", "顏色"] + dealers + ["最低價", "最低盤商", "更新時間"]

    data_rows = []
    for (model, color), dealer_prices in sorted(pivot.items()):
        row = [model, color]
        prices_with_dealer = []
        for d in dealers:
            p = dealer_prices.get(d, "")
            row.append(p)
            if p != "":
                prices_with_dealer.append((p, d))
        if prices_with_dealer:
            min_price, min_dealer = min(prices_with_dealer, key=lambda x: x[0])
        else:
            min_price, min_dealer = "", ""
        row += [min_price, min_dealer, update_time]
        data_rows.append(row)

    try:
        ws = sh.worksheet(SUMMARY_WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=SUMMARY_WORKSHEET_NAME, rows=5000, cols=50)

    ws.clear()
    ws.append_rows([header] + data_rows, value_input_option="USER_ENTERED")
    print(f"✅ 整理後報表已寫入 {len(data_rows)} 筆（共 {len(dealers)} 間盤商）")


def main():
    print("=== 盤商每日價格爬蟲 ===")
    target_urls = get_target_urls()
    if not target_urls or (len(target_urls) == 1 and "example.com" in target_urls[0].get("url", "")):
        print("⚠ 請設定 TARGET_URLS_JSON 環境變數，或在程式內修改 DEFAULT_TARGET_URLS")
        print('  格式: [{"name": "盤商A", "url": "https://盤商網址"}]')
        sys.exit(2)

    model = init_gemini()
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)
    ensure_headers(ws)

    all_rows = []
    driver = None
    try:
        driver = create_chrome_driver()
        for item in target_urls:
            name = item.get("name", "未知")
            url = item.get("url", "")
            if not url:
                continue
            print(f"擷取: {name} - {url[:50]}...")
            try:
                screenshots = capture_full_page_screenshots(driver, url)
                dealer_rows = []
                for i, png in enumerate(screenshots):
                    rows = extract_prices_from_image(model, png, name, url)
                    dealer_rows.extend(rows)
                    if rows:
                        print(f"  [區塊 {i+1}/{len(screenshots)}] 辨識到 {len(rows)} 筆")
                dealer_rows = deduplicate_rows(dealer_rows)
                all_rows.extend(dealer_rows)
                print(f"  -> 合計 {len(dealer_rows)} 筆（已去重）")
            except Exception as e:
                print(f"  [錯誤] {e}")
    finally:
        if driver:
            driver.quit()

    if all_rows:
        ws.clear()
        ensure_headers(ws)
        ws.append_rows(all_rows, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入 {len(all_rows)} 筆至試算表「{WORKSHEET_NAME}」")

        print("=== 開始整理報表 ===")
        build_summary(sh, all_rows)
    else:
        print("⚠ 未辨識到任何價格資料")


if __name__ == "__main__":
    main()
