import os
import asyncio
import aiohttp
import schedule
import time
from flask import Flask, jsonify
from flask_cors import CORS
import threading
from dotenv import load_dotenv
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
        self.combined_promptEnglish = combined_promptEnglish
        self.combined_promptFrench= combined_promptFrench
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
    "hipaaEnabled": True,
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



