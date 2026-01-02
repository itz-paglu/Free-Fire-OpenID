# 🔐 OpenID Fetch API (Auto Cookie Management)

A Flask-based REST API that fetches **OpenID, nickname, and region** from `shop2game.com` using a given user ID (UID), with **automatic cookie/session management**, retry handling, and health monitoring.

---

## ✨ Features

- ✅ Fetch OpenID data using UID  
- 🔄 Automatic cookie & session refresh (TTL-based)
- 🧵 Thread-safe global session cache
- ♻️ Auto-retry on expired/invalid cookies
- ❤️ Health check endpoint
- 🔁 Manual session refresh endpoint
- 🚀 Ready for production / bot integration

---

## 🧩 Tech Stack

- Python 3.8+
- Flask
- Requests
- Threading (for session safety)

---

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/itz-paglu/Free-Fire-OpenID.git
cd Free-Fire-OpenID

📡 API Endpoints
🔹 Get User OpenID

Endpoint
GET /username?uid=<USER_ID>
Example

curl "http://localhost:5000/username?uid=123456789"
Success Response

{
  "success": true,
  "nickname": "PlayerName",
  "region": "BD",
  "account_id": "123456789",
  "open_id": "ABCDEFG123456"
}


Error Response

{
  "success": false,
  "error": "Invalid or expired session",
  "code": 401
}

🔹 Health Check

Endpoint

GET /health


Response

{
  "status": "healthy",
  "session_status": "active",
  "session_age": "12 minutes 30 seconds",
  "timestamp": "2026-01-02T18:40:12.123456"
}

🔹 Force Session Refresh

Endpoint

POST /refresh-session


Response

{
  "success": true,
  "message": "Session will be refreshed on next request"
}

🔐 Session & Cookie Logic

Cookies are fetched automatically from homepage

Session TTL: 25 minutes

Thread-safe session refresh using Lock

Auto-retry (max 2 attempts) if cookie expires

Manual refresh supported via API

⚠️ Important Notes

❌ This project is not affiliated with Free Fire

🧪 API behavior may break if target site changes

📜 Disclaimer

This project is for educational and research purposes only.
The author is not responsible for any misuse or damage caused by this software.

👨‍💻 Author

Tarikul Islam
https: tarikulislam.vercel.app

⭐ Support

If this project helps you:

⭐ Star the repository

🍴 Fork it

🐞 Report issues responsibly
## 📂 Project Structure

