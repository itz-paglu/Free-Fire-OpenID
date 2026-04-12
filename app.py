import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import threading
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

app = Flask(__name__)

# -----------------------------
#  Free Fire OpenID fetch API with DataDome Bypass
#  Using Playwright Chromium Stealth (Render optimized)
# -----------------------------

# Global session cache with thread safety
SESSION_CACHE = {
    "session": None,
    "created_at": None,
    "ttl_minutes": 25,  # Datadome cookies usually valid for a good period
    "lock": threading.Lock()
}


def create_fresh_session():
    """Launch headless browser to solve DataDome and extract cookies"""
    print(f"🔄 Launching Playwright to harvest DataDome cookies at {datetime.now().strftime('%H:%M:%S')}")
    session = requests.Session()
    
    # Base headers that match the browser exactly
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": "https://shop2game.com/"
    })

    try:
        with sync_playwright() as p:
            # Render needs no-sandbox args to run chromium successfully as root/system
            browser = p.chromium.launch(headless=True, args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ])
            context = browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()
            
            # Apply stealth plugin to hide webdriver signatures from DataDome
            stealth_sync(page)
            
            # Navigate to the site and let the JS load
            page.goto("https://shop2game.com", timeout=30000)
            
            # It's crucial to wait a bit so DataDome's Javascript executes and stores the valid cookie
            time.sleep(4)
            
            # Extract cookies and bind them to our lightweight requests Session
            cookies = context.cookies()
            datadome_cookie_found = False
            for c in cookies:
                session.cookies.set(c['name'], c['value'], domain=c.get('domain', ''))
                if "datadome" in c['name'].lower():
                    datadome_cookie_found = True
            
            browser.close()
            
            if datadome_cookie_found:
                print("✅ Valid DataDome cookie harvested successfully!")
            else:
                print("⚠️ Warning: DataDome cookie not found! It might fail.")
            
    except Exception as e:
        print(f"❌ Error harvesting cookies: {e}")
        
    return session


def get_or_refresh_session():
    """Get cached session or create new one if expired (thread-safe)"""
    with SESSION_CACHE["lock"]:
        now = datetime.now()
        
        needs_refresh = (
            SESSION_CACHE["session"] is None or
            SESSION_CACHE["created_at"] is None or
            (now - SESSION_CACHE["created_at"]) > timedelta(minutes=SESSION_CACHE["ttl_minutes"])
        )
        
        if needs_refresh:
            SESSION_CACHE["session"] = create_fresh_session()
            SESSION_CACHE["created_at"] = now
        
        return SESSION_CACHE["session"]


def get_openid_data(account_id, retry_count=0, max_retries=1):
    """Fetch user open_id with DataDome bypass"""
    url = "https://shop2game.com/api/auth/player_id_login"
    payload = {
        "app_id": 100067,
        "login_id": str(account_id)
    }

    # Fetch pre-authorized session
    session = get_or_refresh_session()

    try:
        # Lightweight fast request
        response = session.post(url, json=payload, timeout=10)
        
        # If blocked by datadome, trigger cookie re-harvest (once)
        if response.status_code in [403, 401] or "captcha" in response.text.lower():
            print(f"🔁 Caught DataDome Captcha (Status {response.status_code}). Retrying...")
            if retry_count < max_retries:
                with SESSION_CACHE["lock"]:
                    SESSION_CACHE["session"] = None # Force session invalidation
                return get_openid_data(account_id, retry_count + 1, max_retries)
            else:
                return {"success": False, "error": "Hit captcha and max retries exceeded."}
                
        data = response.json()
        print(f"📥 API Response: {data}")
        
        open_id = data.get("open_id")
        if open_id:
            return {
                "success": True,
                "nickname": data.get("nickname"),
                "region": data.get("region"),
                "account_id": account_id,
                "open_id": open_id,
            }
        else:
            return {
                "success": False,
                "error": data.get("message", "Unknown error"),
                "code": data.get("code"),
                "raw_response": data
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {e}")
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@app.route("/username", methods=["GET"])
def api_openid():
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"success": False, "error": "Missing 'uid' parameter"}), 400

    result = get_openid_data(uid)
    if not result.get("success"):
        return jsonify(result), 400
        
    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    with SESSION_CACHE["lock"]:
        session_status = "active" if SESSION_CACHE["session"] else "not initialized"
        session_age = None
        if SESSION_CACHE["created_at"]:
            age_seconds = (datetime.now() - SESSION_CACHE["created_at"]).seconds
            session_age = f"{age_seconds // 60} minutes {age_seconds % 60} seconds"
    
    return jsonify({
        "status": "healthy",
        "api_mode": "playwright_stealth_local",
        "session_status": session_status,
        "session_age": session_age,
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    print("🚀 Starting Flask API with Playwright Stealth (Render optimized)")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
