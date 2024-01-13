import os
from flask import request, jsonify
from datetime import datetime, timedelta
import schedule
import asyncio
from dotenv import load_dotenv
from vapi_caller import VapiCaller
load_dotenv()

vapi_caller = VapiCaller()
scheduled_jobs = {}
admin_email = f"{os.getenv('ADMIN_EMAIL')}"
admin_password = f"{os.getenv('ADMIN_PASSWORD')}"

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

async def get_calls():
    try:
        all_calls_data = await vapi_caller.get_calls()
        return all_calls_data      
    except Exception as e:
        return f"Error parsing JSON data: {str(e)}", 400


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
    