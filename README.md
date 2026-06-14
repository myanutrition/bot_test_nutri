# Бот «Оцени своё питание» — инструкция по запуску

## Файлы
```
nutrition_bot/
├── bot.py           # Основной файл бота
├── config.py        # ⚙️ Настройки (токен, ссылки)
├── questions.py     # Вопросы теста
├── results.py       # Тексты результатов
└── requirements.txt
```

## 1. Установка

```bash
pip install -r requirements.txt
```

## 2. Настройка

Откройте `config.py` и замените:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # ← токен от @BotFather
```

Остальные ссылки уже вшиты — менять не нужно.

## 3. Запуск

```bash
python bot.py
```

## 4. Что умеет бот

- `/start` — начало работы
- Проверяет подписку на @myanutrition
- Проводит тест из 35 вопросов (7 вариантов ответа кнопками)
- Показывает заголовки разделов при переходе к новому блоку
- Считает баллы и выдаёт один из 5 результатов
- В тексте результата — кликабельные ссылки на страницы услуг
- Кнопки в конце — только релевантные для данного диапазона баллов:
  - 0–35: без кнопок
  - 36–120: «Записаться на разбор»
  - 121–165: «Записаться на разбор» + «Лист ожидания группы»
  - 166–210: «Лист ожидания группы»

## 5. Деплой (опционально)

Для постоянной работы запустите на сервере через `screen`, `tmux` или `systemd`.

Пример systemd-сервиса (`/etc/systemd/system/nutrition_bot.service`):
```ini
[Unit]
Description=Nutrition Quiz Bot
After=network.target

[Service]
WorkingDirectory=/path/to/nutrition_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
