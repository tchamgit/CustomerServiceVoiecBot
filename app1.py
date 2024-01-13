# main.py
from flask import Flask
from flask_cors import CORS
import asyncio
from endpoints import schedule_call, run_call, get_calls, authenticate

app = Flask(__name__)
CORS(app)

app.add_url_rule('/schedule-call', 'schedule_call', schedule_call, methods=['POST'])
app.add_url_rule('/call-customer', 'run_call', run_call, methods=['POST'])
app.add_url_rule('/get-all-calls', 'get_calls', get_calls, methods=['GET'])
app.add_url_rule('/authenticate', 'authenticate', authenticate, methods=['POST'])

if __name__ == '__main__':
    import threading
    from scheduler import run_scheduler, schedule_tasks

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    loop = asyncio.get_event_loop()
    loop.create_task(schedule_tasks())
    loop.run_forever()

    app.run(debug=True)
