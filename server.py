from flask import Flask, request, jsonify, send_from_directory
import os
from anthropic import Anthropic
# import openai  # Uncomment if using OpenAI

app = Flask(__name__, static_folder='static')

# Initialize API client with hardcoded API key
anthropic_client = Anthropic(api_key="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")

# For OpenAI:
# openai.api_key = "your-openai-api-key-here"

STATIC_PROMPT = "You are a helpful assistant. Please provide a concise and useful response to the following query:"

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
    Add your custom processing logic here
    For example: check keywords, format output, filter content, etc.
    """
    # Example processing
    processed = response.strip()
    
    # Add your validation/processing logic here
    # if "specific_keyword" in processed.lower():
    #     processed = "Modified: " + processed
    
    return processed

if __name__ == '__main__':
    app.run(debug=True, port=5000)