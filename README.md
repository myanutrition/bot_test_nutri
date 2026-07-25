# Бот-тест «Мои отношения с едой и телом»

## Файлы

- `main.py` — запуск бота
- `config.py` — настройки (читает `.env`)
- `handlers.py` — вся логика: /start, проверка подписки, тест, /stats, /broadcast
- `quiz_data.py` — вопросы, разборы, результаты
- `database.py` — статистика (SQLite)
- `user_state.py` — прогресс прохождения теста
- `requirements.txt` — зависимости
- `.env.example` — шаблон настроек

## Как запустить на сервере

```bash
cd /home/adminvps
git clone ссылка_на_репозиторий nutrition_quiz
cd nutrition_quiz

pip3 install -r requirements.txt

cp .env.example .env
nano .env
```

В `.env` впиши:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_IDS` — уже стоит твой ID, менять не надо
- `CHANNEL_USERNAME` — уже стоит @myanutrition

## Запуск через systemd

```bash
sudo nano /etc/systemd/system/nutrition_quiz.service
```

Вставь:
```ini
[Unit]
Description=Nutrition Quiz Bot
After=network.target

[Service]
WorkingDirectory=/home/adminvps/nutrition_quiz
ExecStart=/usr/bin/python3 /home/adminvps/nutrition_quiz/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nutrition_quiz
sudo systemctl start nutrition_quiz
sudo systemctl status nutrition_quiz
```

## Команды

- `/start` — запуск теста
- `/stats` — статистика (только для тебя)
- `/broadcast` — рассылка всем, кто прошёл тест
