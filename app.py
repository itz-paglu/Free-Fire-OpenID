from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
from camoufox.sync_api import Camoufox
import threading

app = Flask(__name__)
BASE_URL = "https://shop2game.com"

# Cookie cache — প্রতি request-এ browser খুলবে না
COOKIE_CACHE = {
    "cookies": None,
    "expires_at": None,
    "lock": threading.Lock()
}
COOKIE_TTL_MINUTES = 20


def get_cached_cookies():
    """Cookie cache থেকে নাও, না থাকলে browser দিয়ে আনো"""
    with COOKIE_CACHE["lock"]:
        now = datetime.now()

        if (
            COOKIE_CACHE["cookies"] is None or
            COOKIE_CACHE["expires_at"] is None or
            now >= COOKIE_CACHE["expires_at"]
        ):
            print("🦊 Launching Camoufox for fresh cookies...")
            cookies = _fetch_cookies_via_browser()
            if cookies:
                COOKIE_CACHE["cookies"] = cookies
                COOKIE_CACHE["expires_at"] = now + timedelta(minutes=COOKIE_TTL_MINUTES)
                print(f"✅ Cookies cached for {COOKIE_TTL_MINUTES} minutes")
            return cookies
        else:
            remaining = (COOKIE_CACHE["expires_at"] - now).seconds // 60
            print(f"✓ Using cached cookies ({remaining} min remaining)")
            return COOKIE_CACHE["cookies"]


def _fetch_cookies_via_browser():
    """Camoufox দিয়ে DataDome cookie আনো"""
    try:
        with Camoufox(headless=True, geoip=True) as browser:
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            cookies = page.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            print(f"📦 Cookies: {list(cookie_dict.keys())}")

            if "datadome" not in cookie_dict:
                print("⚠️ datadome cookie missing!")
                return None

            return cookie_dict
    except Exception as e:
        print(f"❌ Browser error: {e}")
        return None


def _get_headers():
    host = urlparse(BASE_URL).netloc
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": host,
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Mobile Safari/537.36"
        ),
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    }


def get_openid_data(account_id):
    payload = {"app_id": 100067, "login_id": str(account_id)}
    url = f"{BASE_URL}/api/auth/player_id_login"

    cookies = get_cached_cookies()
    if not cookies:
        return {"success": False, "error": "Failed to obtain cookies"}

    try:
        response = requests.post(url, headers=_get_headers(), cookies=cookies, json=payload, timeout=15)
        data = response.json()
        print(f"📥 Response: {data}")

        # DataDome আবার block করলে cache clear করো
        if "captcha-delivery.com" in str(data):
            print("🔄 DataDome blocked, clearing cookie cache...")
            with COOKIE_CACHE["lock"]:
                COOKIE_CACHE["cookies"] = None
            return {"success": False, "error": "Blocked by DataDome, please retry"}

        open_id = data.get("open_id")
        if open_id:
            return {
                "success": True,
                "nickname": data.get("nickname"),
                "region": data.get("region"),
                "account_id": account_id,
                "open_id": open_id,
            }
        return {
            "success": False,
            "error": data.get("message", "Unknown error"),
            "code": data.get("code"),
            "raw_response": data
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/username", methods=["GET"])
def api_openid():
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"success": False, "error": "Missing 'uid' parameter"}), 400
    result = get_openid_data(uid)
    return jsonify(result), 200 if result.get("success") else 500


@app.route("/health", methods=["GET"])
def health_check():
    with COOKIE_CACHE["lock"]:
        has_cookies = COOKIE_CACHE["cookies"] is not None
        expires = COOKIE_CACHE["expires_at"].isoformat() if COOKIE_CACHE["expires_at"] else None
    return jsonify({
        "status": "healthy",
        "cookies_cached": has_cookies,
        "cache_expires_at": expires,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/refresh-cookies", methods=["POST"])
def refresh_cookies():
    with COOKIE_CACHE["lock"]:
        COOKIE_CACHE["cookies"] = None
        COOKIE_CACHE["expires_at"] = None
    return jsonify({"success": True, "message": "Cookie cache cleared"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
