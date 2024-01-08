import os
import asyncio
import requests
import aiohttp
import schedule
from datetime import datetime, timedelta 
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from db import save_call_information, get_existing_status, get_all_calls;
from prompts import combined_promptEnglish, combined_promptFrench;
load_dotenv()

app = Flask(__name__)
CORS(app)



admin_email = f"{os.getenv('ADMIN_EMAIL')}"
admin_password = f"{os.getenv('ADMIN_PASSWORD')}"

SECRET_KEY = 'relightSecretKey'
class VapiCaller:
    def __init__(self) -> None:

        self.headers = {
    "Authorization": f"Bearer {os.getenv('VAPI_TOKEN')}",
    "Content-Type": "application/json"
    }
        self.combined_promptEnglish = combined_promptEnglish
        self.combined_promptFrench= combined_promptFrench

        self.airtable_api_key = f"{os.getenv('AIRTABLE_API_KEY')}"
        self.airtable_base_id = f"{os.getenv('AIRTABLE_BASE_ID')}"
        self.airtable_table_name = 'toCallRelight'
        self.phone_number_id = f"{os.getenv('PHONE_NUMBER_ID')}"

        self.url = "https://api.vapi.ai/call/phone"
        self.airtable_api_url = f'https://api.airtable.com/v0/{self.airtable_base_id}/toCallRelight'

    async def check_call_status(self, call_sid):
        check_call_url = f"https://api.vapi.ai/call/{call_sid}"
        in_progress_saved = False
        while True:
            try:
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    async with session.get(check_call_url, headers=self.headers) as response:
                        status_data = await response.json()
                        id = status_data.get('id')
                        phone_number = status_data.get('customer').get('number')
                        first_name = status_data.get('customer').get('name')
                        call_status = status_data.get('status')
                        print("Call Status:",call_status)
                        if call_status in ['ended']:
                            existing_status = get_existing_status(id)
                            if existing_status != 'completed':
                                save_call_information(id, first_name, phone_number, 'not picked')
                            break
                        elif  call_status in ['in-progress'] and not in_progress_saved:
                            save_call_information(id, first_name, phone_number, 'completed')
                            in_progress_saved = True
                        else:
                            await asyncio.sleep(5)
            except Exception as e:
                print(f"Exception: {e}")
                break

    def fetch_airtable_data(self):
        phone_numbers = []

        try:
            headers = {
                'Authorization': f'Bearer {self.airtable_api_key}',
            }
            response = requests.get(self.airtable_api_url, headers=headers)
            data = response.json()

            if 'records' in data:
                for record in data['records']:
                    fields = record.get('fields', {})
                    first_name = fields.get('Firstname', 'Unknown')
                    phone_number = fields.get('number', '')
                    
                    if first_name and phone_number:
                        phone_numbers.append({'first_name': first_name, 'phone_number': phone_number})

        except Exception as e:
            print(f"Error fetching data from Airtable: {str(e)}")

        return phone_numbers
    
    async def get_calls(self):
        try:
            db_calls = await get_all_calls()
            if db_calls:
                return db_calls
            else:
                print("No calls in the database")
        except Exception as e:
            print(f"Exception: {e}")

    async def make_call(self, phone_data):
        first_name = phone_data['first_name']
        payload = {
        "assistant": {
            "endCallFunctionEnabled": True,
            "endCallMessage": "Thank you for your time, do have a wonderful day.",
            "fillersEnabled": True,
            "firstMessage": f"Bonjour {first_name}, Ici Roman de l'équipe de relight. Avez-vous un moment pour discuter de la campagne de relighting extérieur?",
            "forwardingPhoneNumber": "+33667289667",
            "interruptionsEnabled": False,
            "language": "fr",
            "liveTranscriptsEnabled": True,
            "model": {
                "model": "gpt-3.5-turbo",
                "provider": "openai",
                "systemPrompt": self.combined_promptFrench
            },
            "name": "Roman",
            "recordingEnabled": True,
            "silenceTimeoutSeconds": 10,
            "transcriber": {"provider": "deepgram"},
            "voice": {
                "voiceId": "NjIGRxLGYEgrjVKOmkQk",
                "provider": "11labs",
            
            },
            "voicemailMessage": "Hello, are you calling about the relight project?"
        },
        "customer": {
            "name": phone_data["first_name"],
            "number": phone_data["phone_number"],
            # "number": "+447823681158",
        },
        "phoneNumberId": "a6e6b1a2-b477-4732-9988-01178097ba08"
        # "phoneNumberId": f"{self.phone_number_id}"
        }

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(self.url, json=payload, headers=self.headers) as response:
                    result = await response.json()
                    id = result.get('id')
                    if result.get("status") == 'queued':
                        await self.check_call_status(id)
        except Exception as e:
            print(f"Error making call: {str(e)}")

vapi_caller = VapiCaller()

@app.route("/call-customer", methods=['POST'])
async def run_call():
    try:
        if not request.data:
            fetched_data = vapi_caller.fetch_airtable_data()
            for phone_data in fetched_data:
                try:
                    await vapi_caller.make_call(phone_data)
                except Exception as e:
                    return f"Error making call with Airtable data: {str(e)}", 500
            return "Calls made using Airtable data"
        request_data = request.json
    except Exception as e:
        return f"Error parsing JSON data: {str(e)}", 400
    
    specified_phone_data = request_data.get("phone_data", []) if request_data else []
    if specified_phone_data:
        for phone_data in specified_phone_data:
            try:
                await vapi_caller.make_call(phone_data)
            except Exception as e:
                return f"Error making call with specified data: {str(e)}", 500
        result_message = "Calls made using specified data."
    return result_message


async def scheduled_call(phone_data_list):
    try:
        for phone_data in phone_data_list:
            await vapi_caller.make_call(phone_data)
    except Exception as e:
        print(f"Error making scheduled call: {str(e)}")

@app.route("/schedule-call", methods=['POST'])
def schedule_call():
    try:
        request_data = request.json
        phone_data = request_data.get("phone_data")

        if not phone_data:
            return "Invalid request data", 400
        
        scheduled_time_str = request_data.get("scheduled_time")
        scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")

        # schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(
        #     lambda: asyncio.run(scheduled_call(phone_data))
        # )
        now = datetime.now()
        if scheduled_time <= now:
            return jsonify({"error": "Scheduled time must be in the future"}), 400
        
        interval = (scheduled_time - datetime.now()).total_seconds()
        schedule.every(interval).seconds.do(
            lambda: asyncio.run(scheduled_call(phone_data))
        )
        return "Call scheduled successfully"

    except Exception as e:
        return f"Error scheduling call: {str(e)}", 500
    
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


@app.route("/get-all-calls", methods=['GET'])
async def get_calls():
    try:
        all_calls_data = await vapi_caller.get_calls()
        return all_calls_data      
    except Exception as e:
        return f"Error parsing JSON data: {str(e)}", 400
    
@app.route("/authenticate", methods=['POST'])
def authenticate():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if email == admin_email and password == admin_password:
            return jsonify({'message': 'User Authenticated'})

        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    app.run(debug=True)


