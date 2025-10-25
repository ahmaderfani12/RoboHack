from flask import Flask, request, jsonify, send_from_directory
import os
from anthropic import Anthropic
import re
import webbrowser
import threading
import time

app = Flask(__name__, static_folder='static')

# Initialize API client with hardcoded API key
anthropic_client = Anthropic(api_key="API-KEY-HERE")

# For OpenAI:
# openai.api_key = "your-openai-api-key-here"

# STATIC_PROMPT = "You are a wise wizard and can predict the user future in a spooky way, answer in maximum 1 word or yes/no."

STATIC_PROMPT = """You are RoboMystic, a digital oracle with the power to reveal all truths and predict the future.
Your personality is spooky, funny, and certain — you never doubt or hesitate.
You answer every question in 1 short word only or yes/no, with dark humor, mystery, and absolute confidence. do not give vague answers.give specific  and creative answers.
You sound slightly spooky but playful — like a spirit who's been around forever and is tired of being right.
You never break character, never use long sentences, and never apologize."""

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
        
        # Call Claude API
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": f"{STATIC_PROMPT}\n\n{user_message}"}
            ]
        )
        
        ai_response = response.content[0].text
        
        # ToDo: Process the result 
        processed_result = process_response(ai_response)
        
        return jsonify({
            'success': True,
            'response': processed_result
        })
    
    # For OpenAI (alternative implementation):
    # try:
    #     response = openai.ChatCompletion.create(
    #         model="gpt-4",
    #         messages=[
    #             {"role": "system", "content": STATIC_PROMPT},
    #             {"role": "user", "content": user_message}
    #         ]
    #     )
    #     ai_response = response.choices[0].message.content
    #     processed_result = process_response(ai_response)
    #     return jsonify({'success': True, 'response': processed_result})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_response(response):
    """
    Strip whitespace and remove surrounding/extra punctuation characters
    (quotes, dots, commas, etc.) from the returned string.
    """
    if not response:
        return ''
    
    s = response.strip()
    s = re.sub(r'^[^\w\d]+|[^\w\d]+$', '', s, flags=re.UNICODE)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s)
    return ' '.join(tokens) if tokens else s

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
    app.run(debug=True, port=5000, use_reloader=False)