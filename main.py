#!/usr/bin/env python3
import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
DB_PATH = "contracts.db"
SHEET_NAME = "Тест"


def extract_contract_number(text: str) -> str:
    """Извлекает номер договора из строки вида '29389196/25 - Яндекс'"""
    if not isinstance(text, str):
        return ""
    match = re.search(r'^([\d/]+)', text.strip())
    return match.group(1) if match else ""


def clean_column_name(col: str) -> str:
    """
    Очищает имя колонки для использования в SQLite.
    Заменяет все символы, кроме букв, цифр и подчеркивания, на подчеркивание.
    """
    # Заменяем все проблемные символы на _
    safe = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ_]', '_', col)
    # Убираем множественные подчеркивания, в начале и в конце
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')
    # Если колонка стала пустой или начинается с цифры, добавляем префикс
    if not safe or safe[0].isdigit():
        safe = "col_" + safe
    return safe


def get_google_sheet_data(sheet_id: str, credentials_path: str = "credentials.json") -> pd.DataFrame:
    """Подключается к Google Sheets API и возвращает данные с листа 'Тест'."""
    creds = None

    # Пытается загрузить старый токен
    if Path("token.json").exists():
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Если его нет то файл с токеном появляется при первой авторизации
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Сохранения токена для запусков
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        range_name = f"{SHEET_NAME}!A:Z"
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get("values", [])
        
        if not values:
            raise ValueError("Данные не найдены в таблице")
        
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        return df
    
    except HttpError as err:
        print(f"Ошибка API: {err}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Выгрузка данных из Google Sheets в SQLite")
    parser.add_argument("--sheet-id", required=True, help="ID Google Таблицы")
    parser.add_argument("--date", required=True, help="Дата для фильтрации (ГГГГ-ММ-ДД)")
    args = parser.parse_args()
    # Проверка формата даты
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print("Ошибка: дата должна быть в формате ГГГГ-ММ-ДД")
        return
    
    print(f"Загрузка данных из таблицы {args.sheet_id}, лист '{SHEET_NAME}'...")
    
    df = get_google_sheet_data(args.sheet_id)

    if df.empty:
        print("Нет данных для обработки")
        return

    # Удаляем полностью пустые строки
    df = df.dropna(how='all')
    print(f"Загружено {len(df)} строк (после удаления пустых)")

    print(f"Загружено {len(df)} строк")
    
    # Удаляем колонку "Категория"(по заданию)!
    if "Категория" in df.columns:
        df = df.drop(columns=["Категория"])
        print("Удалена колонка 'Категория'")
    
    # Добавляем название листа(по заданию)!
    df["Название_листа"] = SHEET_NAME
    print("Добавлена колонка 'Название_листа'")
    
    # Извлекаем номер договора
    contract_col = None
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["договор", "contract", "№"]):
            contract_col = col
            break
    
    if contract_col:
        df["Номер_договора"] = df[contract_col].apply(extract_contract_number)
        df = df.drop(columns=[contract_col])
        print(f"Извлечены номера договоров из колонки '{contract_col}'")
    else:
        print("Предупреждение: колонка с договорами не найдена, пропускаем этот шаг.")
    
    # Работа с SQLite
    print("Подключение к SQLite...")
    conn = sqlite3.connect(DB_PATH)
    
    # Очищаем имена колонок для БД
    columns = list(df.columns)
    safe_columns = [clean_column_name(col) for col in columns]
    
    # Выводим информацию о переименовании, если оно было
    for original, safe in zip(columns, safe_columns):
        if original != safe:
            print(f"Колонка '{original}' переименована в '{safe}' для SQLite")
    
    # Создаём таблицу динамически
    create_sql = """
        CREATE TABLE IF NOT EXISTS contracts (
            inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """
    for col in safe_columns:
        create_sql += f', "{col}" TEXT'
    create_sql += "\n)"
        

    cursor = conn.cursor()
    try:
        cursor.execute(create_sql)
    except sqlite3.OperationalError as e:
        print(f"Ошибка создания таблицы: {e}")
        print("SQL запрос:", create_sql)
        raise
    
    # Если хотим удалять старые данные за указанную дату
    date_column_name = "Дата_создания_заказа"
    
    if date_column_name in df.columns:
        cursor.execute(f'DELETE FROM contracts WHERE "{date_column_name}" = ?', (args.date,))
        print(f" Удалены старые записи за {args.date}")
    else:
        print("Колонка с датой не найдена — удаляем все записи")
        cursor.execute("DELETE FROM contracts")
    
    # Вставляем новые данные
    placeholders = ",".join(["?" for _ in safe_columns])
    insert_sql = f'INSERT INTO contracts ("{"\", \"".join(safe_columns)}") VALUES ({placeholders})'
    
    # Преобразуем DataFrame в список кортежей
    rows = [tuple(row) for row in df.to_numpy()]
    
    try:
        cursor.executemany(insert_sql, rows)
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Ошибка вставки данных: {e}")
        print("SQL запрос:", insert_sql)
        print("Пример данных:", rows[0] if rows else "Нет данных")
        raise
    
    print(f"Вставлено {len(rows)} строк в {DB_PATH}")
    
    # Результат вывод 
    print("\n Результат в базе данных ")
    df_result = pd.read_sql_query("SELECT * FROM contracts", conn)
    print(df_result.to_string())
    
    conn.close()


if __name__ == "__main__":
    main()