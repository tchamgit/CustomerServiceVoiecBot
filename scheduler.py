# scheduler.py
import asyncio
from datetime import datetime, timedelta
import time
import schedule
from vapi_caller import VapiCaller
from endpoints import scheduled_call
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

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)
        

