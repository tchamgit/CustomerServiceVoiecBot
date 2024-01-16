# vapi_caller.py
import os
from airtable import airtable
import requests
import aiohttp
import asyncio
from prompts import combined_promptEnglish, combined_promptFrench
from db import save_call_information, get_existing_status, get_all_calls

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
            if db_calls:
                return db_calls
            else:
                print("No calls in the database")
        except Exception as e:
            print(f"Exception: {e}")

    async def make_call(self, phone_data):
        first_name = phone_data['first_name']
        fieldId = phone_data.get('id', '') 
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
        },
        "phoneNumberId": f"{self.phone_number_id}"
        }

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(self.url, json=payload, headers=self.headers) as response:
                    result = await response.json()
                    id = result.get('id')
                    if result.get("status") == 'queued':
                        if fieldId != '':
                            await self.check_call_status(id, fieldId)
                        else:
                            await self.check_call_status(id)
        except Exception as e:
            print(f"Error making call: {str(e)}")
