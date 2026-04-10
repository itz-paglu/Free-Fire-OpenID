from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# -----------------------------
#  free fire open id fetch API with auto cookie management
#  credits: https:tarikulislam.vercel.app
# -----------------------------

# Global session cache with thread safety
SESSION_CACHE = {
    "session": None,
    "created_at": None,
    "ttl_minutes": 25,  # Refresh every 25 minutes
    "lock": threading.Lock()
}


def create_fresh_session(base_url):
    """Create a new session with fresh cookies"""
    try:
        session = requests.Session()
        
        # Visit homepage to get initial cookies
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = session.get(base_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Fresh session created at {datetime.now().strftime('%H:%M:%S')}")
            print(f"📦 Cookies obtained: {list(session.cookies.keys())}")
            return session
        else:
            print(f"⚠️ Homepage returned status: {response.status_code}")
            return session
            
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return requests.Session()


def get_or_refresh_session(base_url):
    """Get cached session or create new one if expired (thread-safe)"""
    with SESSION_CACHE["lock"]:
        now = datetime.now()
        
        # Check if session needs refresh
        needs_refresh = (
            SESSION_CACHE["session"] is None or
            SESSION_CACHE["created_at"] is None or
            (now - SESSION_CACHE["created_at"]) > timedelta(minutes=SESSION_CACHE["ttl_minutes"])
        )
        
        if needs_refresh:
            SESSION_CACHE["session"] = create_fresh_session(base_url)
            SESSION_CACHE["created_at"] = now
            print(f"🔄 Session refreshed. Next refresh in {SESSION_CACHE['ttl_minutes']} minutes")
        else:
            time_left = SESSION_CACHE["ttl_minutes"] - (now - SESSION_CACHE["created_at"]).seconds // 60
            print(f"✓ Using cached session. {time_left} minutes remaining")
        
        return SESSION_CACHE["session"]


def _get_openid_headers(base_url):
    """Generate request headers"""
    host = urlparse(base_url).netloc
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": host,
        "Origin": base_url,
        "Referer": base_url,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    }


def get_openid_data(account_id, retry_count=0, max_retries=2):
    """Get OpenID data with automatic retry on cookie expiry"""
    payload = {
        "app_id": 100067,
        "login_id": str(account_id)
    }

    base_url = "https://shop2game.com"
    url = f"{base_url}/api/auth/player_id_login"
    
    # Get session with valid cookies
    session = get_or_refresh_session(base_url)
    headers = _get_openid_headers(base_url)

    try:
        response = session.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        print(f"📥 API Response: {data}")
        
        # Check if cookie expired (common error patterns)
        error_indicators = [
            data.get("code") == 401,
            data.get("code") == 403,
            "invalid" in str(data.get("message", "")).lower(),
            "expired" in str(data.get("message", "")).lower(),
            "unauthorized" in str(data.get("message", "")).lower()
        ]
        
        if any(error_indicators) and retry_count < max_retries:
            print(f"🔁 Cookie might be expired. Retrying... (Attempt {retry_count + 1}/{max_retries})")
            # Force refresh session
            with SESSION_CACHE["lock"]:
                SESSION_CACHE["session"] = None
            time.sleep(1)  # Brief delay before retry
            return get_openid_data(account_id, retry_count + 1, max_retries)
        
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
    """API endpoint to get user info by UID"""
    uid = request.args.get("uid")

    if not uid:
        return jsonify({"success": False, "error": "Missing 'uid' parameter"}), 400

    result = get_openid_data(uid)
    
    if not result.get("success"):
        return jsonify(result), 404 if "not found" in str(result.get("error", "")).lower() else 500
    
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
        "session_status": session_status,
        "session_age": session_age,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/refresh-session", methods=["POST"])
def force_refresh():
    """Manually force session refresh"""
    with SESSION_CACHE["lock"]:
        SESSION_CACHE["session"] = None
        SESSION_CACHE["created_at"] = None
    
    return jsonify({
        "success": True,
        "message": "Session will be refreshed on next request"
    }), 200


if __name__ == "__main__":
    print("🚀 Starting Flask API with Auto Cookie Management")
    print("📍 Endpoints:")
    print("   GET  /username?uid=<user_id>")
    print("   GET  /health")
    print("   POST /refresh-session")
    print("-" * 50)
    
    app.run(host="0.0.0.0", port=5000, debug=True)
