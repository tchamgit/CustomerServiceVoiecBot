import os
import asyncio
import requests
import aiohttp
import schedule
from datetime import datetime, timedelta
import time
from flask import Flask, request, jsonify
from flask.json import dumps
from flask_cors import CORS
from airtable import airtable
import threading
from dotenv import load_dotenv
from db import save_call_information, get_existing_status, get_all_calls, get_settings, save_settings, update_settings;
from prompts import combined_promptEnglish, combined_promptFrench;
load_dotenv()

app = Flask(__name__)
CORS(app)

admin_email = f"{os.getenv('ADMIN_EMAIL')}"
admin_password = f"{os.getenv('ADMIN_PASSWORD')}"
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

        self.airtable_api_key = f"{os.getenv('AIRTABLE_API_KEY')}"
        self.airtable_base_id = f"{os.getenv('AIRTABLE_BASE_ID')}"
        self.airtable_table_name = 'toCallRelight'
        self.phone_number_id = f"{os.getenv('PHONE_NUMBER_ID')}"

        self.url = "https://api.vapi.ai/call/phone"
        self.airtable_api_url = f'https://api.airtable.com/v0/{self.airtable_base_id}/toCallRelight'


    async def check_call_status(self, call_sid, fieldId=None):
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
                            if fieldId is not None:
                                await self.update_airtable_status(fieldId, 'Appel IA 1')
                        else:
                            await asyncio.sleep(5)

            except Exception as e:
                print(f"Exception: {e}")
                break

    async def update_airtable_status(self, record_id, new_status):
        try:
            airtable_instance = airtable.Airtable(self.airtable_base_id, self.airtable_api_key)
            data = {"Relation": new_status}
            update_result = airtable_instance.update('toCallRelight', record_id, data)

            if update_result:
                print("Airtable status updated successfully")
                return True
            else:
                print("Airtable status update unsuccessful")
                return False
        except Exception as e:
            print(f"Error updating Airtable status: {str(e)}")

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
                    id = record.get('id', '')
                    fields = record.get('fields', {})
                    first_name = fields.get('Firstname', 'Unknown')
                    phone_number = fields.get('number', '')
                    relation = fields.get('Relation', 'Unknown')
                    statut_dossier = fields.get('Statut dossier', 'Unknown')
                    if first_name and phone_number:
                        phone_numbers.append({"id": id, 'first_name': first_name, 'phone_number': phone_number,"relation": relation, "statut_dossier": statut_dossier })

        except Exception as e:
            print(f"Error fetching data from Airtable: {str(e)}")

        return phone_numbers
    
    async def get_calls(self):
        try:
            db_calls = await get_all_calls()
            print(db_calls)
            if db_calls:
                return db_calls
            else:
                print("No calls in the database")
        except Exception as e:
            print(f"Exception: {e}")

    async def make_call(self, phone_data):
        first_name = phone_data.get('first_name')
        phone_number = phone_data.get('phone_number')
        fieldId = phone_data.get('id', '') 

        if not first_name or not phone_number:
            raise ValueError("First name and phone number are required")

        settings = await get_settings('customerIntroductoryCallRelightFR')
        if not settings:
            raise ValueError("Settings could not be retrieved")
        
        first_message = settings.get('first_message', '').replace('{first_name}', first_name)
        system_prompt = settings.get('prompt', '')
        language = settings.get('language', '')
        payload = { 
        "assistant": {
            "endCallFunctionEnabled": True,
            "endCallMessage": "Thank you for your time, do have a wonderful day.",
            "fillersEnabled": True,
            "firstMessage": first_message,
            "forwardingPhoneNumber": "+33667289667",
            "interruptionsEnabled": False,
            "language": language,
            "liveTranscriptsEnabled": True,
            "model": {
                "model": "gpt-3.5-turbo",
                "provider": "openai",
                "systemPrompt": system_prompt
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
        },
        "phoneNumberId": f"{self.phone_number_id}"
        }

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(self.url, json=payload, headers=self.headers) as response:
                    result = await response.json()
                    call_id = result.get('id')
                    if result.get("status") == 'queued':
                        if fieldId != '':
                            await self.check_call_status(call_id, fieldId)
                        else:
                            await self.check_call_status(call_id)
                    return True
        except Exception as e:
            print(f"Error making call: {str(e)}")
            

vapi_caller = VapiCaller()

async def schedule_airtable_fetch():
        try:
            phone_data_list = vapi_caller.fetch_airtable_data()
            filtered_data = [
                phone_data for phone_data in phone_data_list
                if phone_data.get("relation") == "Séquence en cours"
                and phone_data.get("statut_dossier") == "Rencensement en attente"
            ]
            if filtered_data:
                await scheduled_call(filtered_data)
        except Exception as e:
            print(f"Error scheduling Airtable fetch: {str(e)}")

async def schedule_tasks():
    while True:
        now = datetime.now()
        scheduled_time = datetime(now.year, now.month, now.day, 13, 0)  
        if now < scheduled_time:
            await asyncio.sleep((scheduled_time - now).total_seconds())
            await schedule_airtable_fetch()
        else:
            tomorrow = now + timedelta(days=1)
            scheduled_time_tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 13, 0)
            await asyncio.sleep((scheduled_time_tomorrow - now).total_seconds())
            await schedule_airtable_fetch()


async def scheduled_call(phone_data_list, tag=None):
        try:
            for phone_data in phone_data_list:
                await vapi_caller.make_call(phone_data)
        except Exception as e:
            print(f"Error making scheduled call: {str(e)}")
        finally:
            if tag in scheduled_jobs:
                schedule.clear(tag, scheduled_jobs[tag])
                del scheduled_jobs[tag]

@app.route("/schedule-call", methods=['POST'])
def schedule_call():
    try:
        request_data = request.json
        phone_data = request_data.get("phone_data")

        if not phone_data:
            return "Invalid request data", 400
        
        scheduled_time_str = request_data.get("scheduled_time")
        scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")

        now = datetime.now()
        if scheduled_time <= now:
            return jsonify({"error": "Scheduled time must be in the future"}), 400
        
        tag = f'scheduled_call_{scheduled_time_str}'
        job = schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(
            lambda: asyncio.run(scheduled_call(phone_data))
        )
        scheduled_jobs[tag] = job
   
        return "Call scheduled successfully"

    except Exception as e:
        return f"Error scheduling call: {str(e)}", 500
    
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

@app.route("/get-all-calls", methods=['GET'])
async def get_calls():
    try:
        all_calls_data = await vapi_caller.get_calls()
        return all_calls_data      
    except Exception as e:
        return f"Error parsing JSON data: {str(e)}", 400
        
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
    loop.create_task(schedule_tasks())
    loop.run_forever()



