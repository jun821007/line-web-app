#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盤商每日價格爬蟲 - 截圖 → Gemini 識別 → 寫入 Google 試算表
試算表: 1EBmhc6YKZBuwnASCPorrRjvdsHWf7IPASr3-ZJ5DuAM
分頁: 新機總表
抬頭: 盤商 | 盤商網頁 | 型號 | 價格 | 最後更新時間
"""

import os
import sys
import json
import base64
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# ========== 設定 ==========
SPREADSHEET_ID = "1EBmhc6YKZBuwnASCPorrRjvdsHWf7IPASr3-ZJ5DuAM"
WORKSHEET_NAME = "新機總表"
HEADERS = ["盤商", "盤商網頁", "型號", "價格", "最後更新時間"]

# 盤商網址：格式 [{"name": "盤商名稱", "url": "https://..."}]
# 可透過環境變數 TARGET_URLS_JSON 覆蓋（JSON 字串）
DEFAULT_TARGET_URLS = [
    {"name": "範例盤商", "url": "https://example.com/price-list"},
]

# 依 API 實際查詢：此 Key 支援 gemini-2.5-pro（1.5 系列不支援）
GEMINI_MODEL = "gemini-2.5-pro"


def get_target_urls():
    raw = os.environ.get("TARGET_URLS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return DEFAULT_TARGET_URLS


def get_gspread_client():
    """取得 gspread 連線：支援本機 JSON 檔 或 GitHub Actions 的 GSPREAD_CREDENTIALS_JSON"""
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


def capture_page_png(driver, url):
    driver.get(url)
    driver.implicitly_wait(5)
    return driver.get_screenshot_as_png()


def extract_prices_from_image(model, image_bytes, source_name, source_url):
    """用 Gemini 從截圖辨識型號與價格"""
    prompt = """這是一張盤商報價單截圖。請從圖片中辨識「型號」與「價格」。
回傳格式必須是 JSON 陣列，每個元素為 {"model": "型號", "price": 數字}。
範例: [{"model": "iPhone 16 128G", "price": 28500}, {"model": "iPhone 16 Pro 256G", "price": 36500}]
若無法辨識或圖中無報價，回傳 []。只回傳 JSON，不要其他說明。"""

    img_part = {
        "mime_type": "image/png",
        "data": image_bytes,
    }
    try:
        response = model.generate_content([prompt, img_part])
        text = response.text.strip()
        # 去除可能的 markdown 包裝
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
            p = item.get("price") or item.get("價格") or 0
            try:
                p = int(p)
            except (TypeError, ValueError):
                p = 0
            if m:
                rows.append([source_name, source_url, str(m), p, now])
        return rows
    except Exception as e:
        print(f"  [Gemini] 辨識失敗: {e}")
        return []


def ensure_headers(ws):
    """確保試算表有正確抬頭"""
    row1 = ws.row_values(1)
    if row1 != HEADERS:
        ws.update("A1:E1", [HEADERS])


def main():
    print("=== 盤商每日價格爬蟲 ===")
    target_urls = get_target_urls()
    if not target_urls or (len(target_urls) == 1 and "example.com" in target_urls[0].get("url", "")):
        print("⚠ 請設定 TARGET_URLS_JSON 環境變數，或在程式內修改 DEFAULT_TARGET_URLS")
        print("  格式: [{\"name\": \"盤商A\", \"url\": \"https://盤商網址\"}]")
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
                png = capture_page_png(driver, url)
                rows = extract_prices_from_image(model, png, name, url)
                all_rows.extend(rows)
                print(f"  -> 辨識到 {len(rows)} 筆")
            except Exception as e:
                print(f"  [錯誤] {e}")
    finally:
        if driver:
            driver.quit()

    if all_rows:
        ws.append_rows(all_rows, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入 {len(all_rows)} 筆至試算表「{WORKSHEET_NAME}」")
    else:
        print("⚠ 未辨識到任何價格資料")


if __name__ == "__main__":
    main()
