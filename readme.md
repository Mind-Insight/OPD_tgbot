```bash
git clone https://github.com/Mind-Insight/OPD_tgbot.git
```

```bash
cd OPD_tgbot
```

```bash
cp .env.example .env
```

в .env
```bash
BOT_TOKEN=токена_бота
MONGO_URI=mongodb://admin:pswd@localhost:27017/?authSource=admin
MONGO_DB_NAME=test_bot_db
```


```bash
docker compose up -d
```

```bash
python3 -m venv venv

source venv/bin/activate
или
source venv/Scripts/activate

pip install -r requirements.txt
```

```bash
python main.py
```
