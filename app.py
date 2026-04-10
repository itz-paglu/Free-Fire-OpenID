from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)

# -----------------------------
#  free fire open id fetch API (no session caching - fresh session per request)
#  credits: https:tarikulislam.vercel.app
# -----------------------------

BASE_URL = "https://shop2game.com"


def create_fresh_session():
    """Create a new session with fresh cookies for every request"""
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        response = session.get(BASE_URL, headers=headers, timeout=15)
        print(f"✅ Fresh session created at {datetime.now().strftime('%H:%M:%S')} | Status: {response.status_code}")
        print(f"📦 Cookies obtained: {list(session.cookies.keys())}")
    except Exception as e:
        print(f"❌ Error during session init: {e}")

    return session


def _get_openid_headers():
    """Generate request headers"""
    host = urlparse(BASE_URL).netloc
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": host,
        "Origin": BASE_URL,
        "Referer": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    }


def get_openid_data(account_id):
    """Get OpenID data using a brand new session every time"""
    payload = {
        "app_id": 100067,
        "login_id": str(account_id)
    }

    url = f"{BASE_URL}/api/auth/player_id_login"

    # Always create fresh session — no cache
    session = create_fresh_session()
    headers = _get_openid_headers()

    try:
        response = session.post(url, headers=headers, json=payload, timeout=15)
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
    finally:
        session.close()  # Session শেষে বন্ধ করে দাও


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
    return jsonify({
        "status": "healthy",
        "session_mode": "no-cache (fresh per request)",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    print("🚀 Starting Flask API — No Session Cache Mode")
    print("📍 Endpoints:")
    print("   GET  /username?uid=<user_id>")
    print("   GET  /health")
    print("-" * 50)

    app.run(host="0.0.0.0", port=5000, debug=True)
