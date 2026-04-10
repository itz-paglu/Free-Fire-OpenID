from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from datetime import datetime
from playwright.sync_api import sync_playwright

app = Flask(__name__)

BASE_URL = "https://shop2game.com"


def get_real_browser_cookies():
    """Playwright দিয়ে real browser চালিয়ে DataDome cookie নিয়ে আসো"""
    print("🌐 Launching headless browser to fetch real cookies...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Mobile Safari/537.36"
            ),
            viewport={"width": 390, "height": 844},
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9"
            }
        )

        # Bot detection এড়াতে
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        try:
            # Homepage visit করো যাতে DataDome cookie সেট হয়
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            print(f"✅ Page loaded: {page.title()}")

            # কিছুটা human-like delay
            page.wait_for_timeout(2000)

            # সব cookie নাও
            cookies = context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            print(f"📦 Cookies fetched: {list(cookie_dict.keys())}")

            return cookie_dict

        except Exception as e:
            print(f"❌ Browser error: {e}")
            return {}

        finally:
            browser.close()


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
    """প্রতিটি request-এ real browser cookie দিয়ে API call করো"""
    payload = {
        "app_id": 100067,
        "login_id": str(account_id)
    }

    url = f"{BASE_URL}/api/auth/player_id_login"

    # Real browser থেকে cookie আনো
    cookies = get_real_browser_cookies()

    if not cookies:
        return {"success": False, "error": "Failed to obtain browser cookies"}

    headers = _get_openid_headers()

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=15
        )
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
        return jsonify(result), 404 if "not found" in str(result.get("error", "")).lower() else 500

    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "mode": "playwright-real-browser-cookies",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    print("🚀 Starting Flask API — Playwright Cookie Mode")
    print("📍 Endpoints:")
    print("   GET  /username?uid=<user_id>")
    print("   GET  /health")
    print("-" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
