from flask import Flask, request, jsonify
from curl_cffi import requests as cf_requests
from datetime import datetime

app = Flask(__name__)
BASE_URL = "https://shop2game.com"


def get_openid_data(account_id):
    payload = {"app_id": 100067, "login_id": str(account_id)}
    url = f"{BASE_URL}/api/auth/player_id_login"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    try:
        # Chrome120 fingerprint দিয়ে impersonate করো
        session = cf_requests.Session(impersonate="chrome120")

        # প্রথমে homepage visit করে cookie নাও
        session.get(BASE_URL, timeout=15)

        # তারপর API call করো
        response = session.post(url, headers=headers, json=payload, timeout=15)
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
    return jsonify(result), 200 if result.get("success") else 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "mode": "curl-cffi-chrome120",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
