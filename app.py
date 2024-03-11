import os
import asyncio
import aiohttp
import schedule
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests
from flask.json import dumps
from dotenv import load_dotenv
from db import save_call_information,  get_settings, save_settings, update_settings;
from prompts import combined_promptEnglish, combined_promptFrench;
load_dotenv()

app = Flask(__name__)
CORS(app)

scheduled_jobs = {}
ALLOWED_LANGUAGES = {"en"," en-US", "en-AU", "en-GB", "en-NZ", "en-IN", "fr", "fr-CA", "de", "hi", "hi-Latn", "pt", "pt-BR", "es", "es-419"}
class VapiCaller:
    def __init__(self) -> None:

        self.headers = {
    "Authorization": f"Bearer {os.getenv('VAPI_TOKEN')}",
    "Content-Type": "application/json"
    }
        self.combined_promptFrench= combined_promptFrench
        self.combined_promptEnglish = combined_promptEnglish
        self.phone_number_id = f"{os.getenv('PHONE_NUMBER_ID')}"

        self.url = "https://api.vapi.ai/call/phone"


    async def create_assistant(self):
        url = "https://west-api.vapi.ai/assistant"
        
        payload = { 
        "clientMessages": ["transcript", "hang", "function-call", "speech-update", "metadata", "conversation-update"],
    "dialKeypadFunctionEnabled": True,
    "endCallFunctionEnabled": True,
    "endCallMessage":"Merci de nous avoir appelés aujourd'hui. Si vous avez d'autres questions, n'hésitez pas à nous rappeler. Au revoir!",
    "endCallPhrases": ["Merci et au revoir", "Merci pour votre appel"],
    "firstMessage": "Bonjour et merci d'avoir appelé Obby Share, comment puis-je vous aider aujourd'hui?",
    "forwardingPhoneNumber": "+447823681158",
    "hipaaEnabled": False,
    "llmRequestDelaySeconds": 0.1,
    "maxDurationSeconds": 1800,
    "metadata": {},
    "model": {
        "functions": [
            {
                "async": True,
                "description": "Function to retrieve customer's account details",
                "name": "getAccountDetails",
                "parameters": {
                    "properties": {},
                    "required": ["<string>"],
                    "type": "object"
                }
            }
        ],
        "maxTokens": 525,
        "messages": [
            {
                "content": "Y a-t-il autre chose que je puisse vous aider aujourd'hui?",
                "function_call": {},
                "role": "assistant",
                "tool_calls": [{}]
            }
        ],
        "model": "gpt-3.5-turbo",
        "provider": "openai",
        "temperature": 1,
    },
    "name": "Obby ShareCustomerBot",
    "recordingEnabled": True,
    "responseDelaySeconds": 0.4,
    "serverMessages": ["end-of-call-report", "status-update", "hang", "function-call"],
    "silenceTimeoutSeconds": 30,
    "transcriber": {
        "language": "fr",
        "model": "nova-2",
        "provider": "deepgram"
    },
    "voice": {
        "provider": "11labs",
        "voiceId": "7S1JYc8XqhAqr08QhUO4"
    },
    "voicemailMessage": "Vous avez atteint Obby Share. Nous ne sommes pas en mesure de répondre à votre appel pour le moment. Veuillez laisser un message et nous vous répondrons dans les plus brefs délais."
        }

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status == 201:
                        result = await response.json()
                        print(result)
                        return {"success": True, "data": result}
                    else:
                        error_message = await response.text()
                        print(f"Error: {response.status}, Message: {error_message}")
                        return {"success": False, "error": f"HTTP Error {response.status}: {error_message}"}       
        except Exception as e:
            print(f"Exception: {str(e)}")
            return {"success": False, "error": f"Exception: {str(e)}"}
        
vapi_caller = VapiCaller()
    
@app.route("/create-assistant", methods=['POST'])
async def create_assistant_endpoint():
    try:
        result = await vapi_caller.create_assistant()
        if result["success"]:
            return jsonify({"message": "Assistant created successfully", "data": result["data"]}), 200
        else:
            return jsonify({"error": result["error"]}), 500
    except Exception as e:
        return f"Error scheduling call: {str(e)}", 500
    

@app.route('/import-phone-number', methods=['POST'])
def import_phone_number():
    # Retrieve data from the incoming request
    data = request.json
    assistantId = data.get('assistantId')
    name = data.get('name')
    twilioAccountSid = data.get('twilioAccountSid')
    twilioAuthToken = data.get('twilioAuthToken')
    twilioPhoneNumber = data.get('twilioPhoneNumber')
    
    # Construct the payload for the Twilio API request
    payload = {
        "assistantId": assistantId,
        "name": name,
        "twilioAccountSid": twilioAccountSid,
        "twilioAuthToken": twilioAuthToken,
        "twilioPhoneNumber": twilioPhoneNumber
    }
    
    # Headers for the Twilio API request
    headers = {
        'Authorization': f'Bearer {os.getenv("VAPI_TOKEN")}',
        'Content-Type': 'application/json'
    }
    
    # Make the POST request to Twilio API
    response = requests.post('https://api.vapi.ai/phone-number/import', json=payload, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200 or response.status_code == 201:
        # Return the successful response from Twilio API to the client
        return jsonify(response.json()), 200
    else:
        # Return the error response from Twilio API to the client
        return jsonify(response.json()), response.status_code
    
@app.route("/settings", methods=['GET', 'POST', 'PATCH'])
async def settings():
    try:
        if request.method == 'POST':
            settings_data = request.json
            prompt_name = settings_data.get('prompt_name')
            language = settings_data.get('language')
            first_message = settings_data.get('first_message')
            prompt = settings_data.get('prompt')

            if language not in ALLOWED_LANGUAGES:
                return jsonify({"error": f"Invalid language {language}. Allowed languages are: {', '.join(ALLOWED_LANGUAGES)}"}), 400

            await save_settings(prompt_name, language, first_message, prompt)
            return dumps({"message": "Settings updated"}), 200, {'Content-Type': 'application/json'}
        elif request.method == 'PATCH':
            settings_data =  request.json
            prompt_name = settings_data.get('prompt_name')
            if not prompt_name:
                return jsonify({"error": "prompt_name is required"}), 400
            first_message = settings_data.get('first_message', None)
            prompt = settings_data.get('prompt', None)

            if not prompt_name:
                return jsonify({"error": "prompt_name is required"}), 400
            
            await update_settings(prompt_name, first_message, prompt)
            return dumps({"message": "Settings updated"}), 200, {'Content-Type': 'application/json'}
        else: 
            prompt_name = request.args.get('prompt_name')
            if prompt_name:
                settings = await get_settings(prompt_name)
            else:
                return dumps({"error": "Please provide both prompt_name"}), 400, {'Content-Type': 'application/json'}
            if settings:
                return dumps(settings), 200, {'Content-Type': 'application/json'}
            else:
                return dumps({"error": "Settings not found."}), 404, {'Content-Type': 'application/json'}
    except ValueError as ve:
        return dumps({"error": str(ve)}), 400, {'Content-Type': 'application/json'}
    except Exception as e:
        return dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}

def run_flask_app():
    app.run(debug=True, use_reloader=False)



def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    flask_thread = threading.Thread(target=run_flask_app)
    scheduler_thread = threading.Thread(target=run_scheduler)
    flask_thread.start()
    scheduler_thread.start()
    loop.run_forever()



