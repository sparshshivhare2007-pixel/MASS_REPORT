# 🚀 Mass Report Telegram Bot

Ek powerful Telegram bot jo multiple String Sessions ka use karke kisi bhi Channel, Group, ya User par mass reporting coordinate karta hai. Iska use spam, scams, aur illegal content ko down karne ke liye kiya ja sakta hai.

---

## ✨ Features
- **Interactive Session Addition:** `/make_config` command se ek ke baad ek sessions bhejkar `/done` likhne par auto-save.
- **Triple Category Report:** Ek saath Child Abuse, Scam, aur Violence ki category mein report.
- **Double Impact:** Har account target profile aur uske latest message dono par report karta hai.
- **MongoDB Support:** Aapka data (sessions) hamesha ke liye safe rehta hai.
- **Anti-Flood System:** Reports ke beech mein delays hain taaki aapke accounts ban na hon.

---

## 🛠 Config (Environment Variables)
Deploy karne se pehle ye variables set karein:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | BotFather se mila API Token |
| `API_ID` | my.telegram.org se mila API ID |
| `API_HASH` | my.telegram.org se mila API Hash |
| `MONGO_URL` | MongoDB Atlas ka connection string |
| `ADMIN_ID` | Aapki apni numeric Telegram ID |

---

## 🚀 Deployment Methods

### 1. Heroku (Recommended for Beginners)
1. **GitHub** par apni repository ko fork ya upload karein.
2. Heroku dashboard mein naya app banayein.
3. **Settings > Reveal Config Vars** mein jayein aur upar diye gaye variables bharein.
4. **Deploy** tab mein GitHub connect karke `main` branch ko deploy karein.
5. **Resources** tab mein `worker` ko ON karein.

### 2. VPS Deployment (For 24/7 Power)
VPS par terminal open karein aur ye commands run karein:
```bash
# Repo clone karein
git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
cd your-repo-name

# Requirements install karein
pip3 install -r requirements.txt

# .env file banayein aur details bharein
nano .env

# Bot run karein
python3 main.py
