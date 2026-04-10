from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from datetime import datetime
from camoufox.sync_api import Camoufox

app = Flask(__name__)
BASE_URL = "https://shop2game.com"


def get_real_browser_cookies():
    """Camoufox দিয়ে DataDome bypass করে real cookie আনো"""
    print("🦊 Launching Camoufox to bypass DataDome...")

    with Camoufox(headless=True, geoip=True) as browser:
        page = browser.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            cookies = page.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            print(f"📦 Cookies: {list(cookie_dict.keys())}")

            # datadome cookie আছে কিনা চেক করো
            if "datadome" not in cookie_dict:
                print("⚠️ datadome cookie not found!")
                return {}

            return cookie_dict

        except Exception as e:
            print(f"❌ Browser error: {e}")
            return {}


def _get_openid_headers():
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

    cookies = get_real_browser_cookies()
    if not cookies:
        return {"success": False, "error": "Failed to obtain valid cookies (DataDome blocked)"}

    try:
        response = requests.post(
            url,
            headers=_get_openid_headers(),
            cookies=cookies,
            json=payload,
            timeout=15
        )
        data = response.json()
        print(f"📥 Response: {data}")

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

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/username", methods=["GET"])
def api_openid():
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"success": False, "error": "Missing 'uid' parameter"}), 400
    result = get_openid_data(uid)
    status = 200 if result.get("success") else 500
    return jsonify(result), status


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "mode": "camoufox-datadome-bypass",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    print("🚀 Flask API — Camoufox Mode")
    app.run(host="0.0.0.0", port=5000, debug=True)
