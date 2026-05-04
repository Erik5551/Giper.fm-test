# Выгрузка данных из Google Sheets в SQLite

## Описание проекта

Скрипт загружает данные с листа `Тест` Google-таблицы, очищает их, извлекает номер договора и сохраняет в SQLite.  
При повторном запуске данные за указанную дату перезаписываются, остальные даты не трогаются.

## Требования

- Python 3.10 или выше
- Google аккаунт с доступом к Google Sheets API
- Файл `credentials.json` (создаётся в Google Cloud Console)
- Доступ к таблице (расшарен на почту)

## Этап 1. Настройка доступа к Google Sheets API

### 1.1 Создать проект в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Вверху слева нажмите на выпадающий список проектов → выберите **"NEW PROJECT"**
3. Введите имя проекта (например, `Sheets API Project`)
4. Нажмите **"CREATE"**

### 1.2 Включить Google Sheets API

1. В левом меню: **"APIs & Services"** → **"Library"**
2. В поиске введите `Google Sheets API`
3. Нажмите на карточку **"Google Sheets API"**
4. Нажмите **"ENABLE"**

### 1.3 Настроить экран согласия OAuth (Scopes)

1. В левом меню: **"APIs & Services"** → **"OAuth consent screen"**
2. Выберите **"External"** → нажмите **"CREATE"**
3. Заполните поля:
   - **App name:** `Data Upload Script`
   - **User support email:** выберите свою почту
   - **Developer contact email:** выберите свою почту
4. Нажмите **"SAVE AND CONTINUE"**
   
5. **Добавить Data Access Scopes (разрешения):**
   - Нажмите **"ADD OR REMOVE SCOPES"**
   - В поиске введите `spreadsheets.readonly`
   - Отметьте галочкой `.../auth/spreadsheets.readonly`
   - Нажмите **"UPDATE"**
   - Нажмите **"SAVE AND CONTINUE"**
     
6. **Добавить тестовых пользователей (ВАЖНО!):**
   - Найдите раздел **"Test users"**
   - Нажмите **"ADD USERS"**
   - Введите свою почту (ту, с которой будете запускать скрипт)
   - Нажмите **"ADD"**
   - Нажмите **"SAVE AND CONTINUE"**
  
### 1.4 Создать и скачать credentials.json

1. В левом меню: **"APIs & Services"** → **"Credentials"**
2. Нажмите **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Заполните форму:
   - **Application type:** выберите **"Desktop app"**
   - **Name:** `My Computer`
4. Нажмите **"CREATE"**
5. Во всплывающем окне нажмите на **иконку скачивания** рядом с вашим ID
6. Скачается файл `client_secret_....json` → **переименуйте** в `credentials.json`
7. Положите `credentials.json` в папку с проектом

   
## Этап 2. Установка и запуск

### 2.1 Клонирование

```bash
git clone https://github.com/Erik5551/Giper.fm-test.git
```
### 2.2 Установить зависимости
cd 
```bash
pip install pandas google-auth google-auth-oauthlib google-api-python-client
```
Или через requirements.txt:
```bash
pip install -r requirements.txt
```
### 2.3 Запустить скрипт

Выполните команду в терминале:
```bash
python main.py --sheet-id "1AXGsVD1Dp4YfuKdaSfT5SY0detbbDmmMBzJXsLG7-30" --date "2026-03-01"
```
**Что нужно указать:**
* **`--sheet-id`** — ID таблицы (берётся из URL: `https://google.com<ID>/edit`)
* **`--date`** — дата, за которую нужно записать данные (формат `ГГГГ-ММ-ДД`)

### 2.3 Первый запуск и авторизация
При первом запуске откроется браузер с запросом на вход в Google-аккаунт.
После подтверждения в папке проекта появится файл token.json — он сохраняет сессию и повторный вход не потребуется.

## Этап 3. Выбор базы данных
**Почему SQLite:**

1. **Не требует установки** и настройки отдельного сервера.
2. **Легко работает** с библиотекой `pandas`.
3. **Подходит для небольших объёмов** данных (до десятков тысяч строк).
4. **Легко масштабируется**: при росте данных можно перейти на PostgreSQL без изменения логики работы с таблицами.


