import os
import re
import threading
import time
import webbrowser

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='static')

ORACLE_API_URL = os.getenv("ORACLE_API_URL", "http://127.0.0.1:5000/api/chat")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        response = requests.post(
            ORACLE_API_URL,
            json={"message": user_message},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            return jsonify({'error': data.get('error', 'Unknown error')}), 500

        return jsonify({
            'success': True,
            'response': data.get('response', '')
        })

    except requests.RequestException as exc:
        print(f"Error contacting oracle server: {exc}")
        return jsonify({'error': str(exc)}), 502
    except Exception as exc:
        print(f"Error: {exc}")
        return jsonify({'error': str(exc)}), 500

if __name__ == '__main__':
    def open_browser(delay=1.0, url='http://127.0.0.1:5000/'):
        def _open():
            time.sleep(delay)
            try:
                webbrowser.open_new(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    open_browser(delay=1.0)
    app.run(debug=True, port=5001, use_reloader=False)
