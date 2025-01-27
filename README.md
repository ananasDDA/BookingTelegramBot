# BookingTelegramBot 🏂

$\textsf{\Huge{{\color[rgb]{1.0, 0.7, 0.8}b}{\color[rgb]{1.0, 0.6, 0.7}o}{\color[rgb]{1.0, 0.5, 0.6}a}{\color[rgb]{1.0, 0.4, 0.5}r}{\color[rgb]{1.0, 0.3, 0.4}d~ }{\color[rgb]{1.0, 0.2, 0.3}e}{\color[rgb]{1.0, 0.1, 0.2}d}{\color[rgb]{1.0, 0.0, 0.1}i}{\color[rgb]{0.9, 0.0, 0.2}t}{\color[rgb]{0.8, 0.0, 0.3}i}{\color[rgb]{0.7, 0.0, 0.4}o}{\color[rgb]{0.6, 0.0, 0.5}n}}}$ 

---

Бот для бронирования сноубордов через телеграм бота + интеграция с гугл календарем

---

## Получение credentials.json
для работы с гугл календарем нужно получить credentials.json
инструкция по получению credentials.json:
https://developers.google.com/calendar/api/guides/concepts/auth

**Вот пошаговая инструкция для получения `credentials.json`:**
1. Перейдите в Google Cloud Console
2. Создайте новый проект или выберите существующий
3. В боковом меню найдите "APIs & Services" → "Enabled APIs & services"
4. Нажмите "+ ENABLE APIS AND SERVICES"
5. Найдите "Google Calendar API" и включите его
6. Перейдите в "Credentials" (в боковом меню)
7. Нажмите "CREATE CREDENTIALS" → "OAuth client ID"
8. Выберите "Desktop app"
9. Нажмите "CREATE"
10. Скопируйте credentials.json в корень проекта



## Настройка 🛠

**откройте файл `.public_env` и переименуйте его в `.env`!**

Пройдемся по файлу `.env` и заполним все поля:

### TELEGRAM_BOT_TOKEN
Замените на токен своего бота

### LOGS_CHANNEL_ID
Замените на ID канала, в который будут приходить логи бота
Бота нужно добавить в канал и сделать его администратором.
Чтобы узнать ID канала, нужно переслать любое сообщение из канала в @LeadConverterToolkitBot
**ВАЖНО:** ID канала должен быть отрицательным, например `-1002328687465`


### FIRST_CALENDAR_ID SECOND_CALENDAR_ID
Замените на ID календарей, в которые будут приходить бронирования
ID календаря можно узнать в настройках календаря в Google Calendar

### LOADING_STICKER_ID
Замените на ID стикера, который будет отправляться во время загрузки бронирования
ID стикера можно узнать в настройках стикера в телеграм
или отправив его в @LeadConverterToolkitBot

### ENVIRONMENT
Замените на "local" или "server"

#### Local development "ENVIRONMENT=local"
1. Выполняется стандартный процесс аутентификации через браузер.
2. Генерируется файл token.pickle.
3. Позволяет повторно создавать токен при необходимости.

#### Server mode "ENVIRONMENT=server"
1. Сначала сгенерируйте файл token.pickle локально
   для этого просто запустите бот локально и дождитесь завершения аутентификации
   (она пройдет через браузер)

2. Загрузите файл token.pickle на сервер
   Аутентификация через браузер не выполняется
    команда для загрузки файла на сервер:
    ```bash
    scp token.pickle username@your_server_ip:/path/to/your/project/
    ```
#### Calendar Icons

Вы также можете изменить иконки календаря
вот значения по умолчанию:
- Прошедшая дата: ✖️
- Сегодняшняя дата: ⭕️
- Даты с прошедшими бронированиями: ✔️
- Время, которое занято: 🔴
- Брони пользователя: ⭐️

#### Русская локализация
установите русскую локализацию в системе (например, ubuntu)
```bash
sudo apt-get update && sudo apt-get install language-pack-ru && sudo locale-gen ru_RU.UTF-8
```


## Запуск 🚀

```bash
pip install -r requirements.txt
```

```bash
python my_telebot.py
```
или

(чтобы бот работал в фоновом режиме)
```bash
python my_telebot.py &
```
(для запуска внутри screen)
```bash
screen -dmS booking_telebot python my_telebot.py
```

#### запуск ботак как сервис:
1. создадим файл `booking_telebot.service`
важно, файл должен находиться в директории `/etc/systemd/system/`

2. добавим в него следующий текст:
```bash
[Unit]
Description=Booking Telegram Bot
After=multi-user.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/your/project
ExecStart=/usr/bin/python3 /path/to/your/project/my_telebot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. перезапустим сервис
```bash
sudo systemctl daemon-reload && sudo systemctl enable booking_telebot.service && sudo systemctl start booking_telebot.service
```

4. проверим статус сервиса
```bash
sudo systemctl status booking_telebot.service
```

5. проверим логи сервиса
```bash
sudo journalctl -u booking_telebot.service -f
```
---
также можно остановить сервис
```bash
sudo systemctl stop booking_telebot.service
```

и удалить сервис
```bash
sudo systemctl disable booking_telebot.service && sudo systemctl remove booking_telebot.service
```
