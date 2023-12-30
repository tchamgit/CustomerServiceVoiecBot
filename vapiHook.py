from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/vapi-webhook", methods=['POST', 'GET'])
async def vapi_webhook():
    try:
        status_data = request.json
        if status_data:
            message_type = status_data.get('message', {}).get('type')
            if message_type == 'status-update':
                call_status = status_data.get('message', {}).get('status')
                print(f'Call Status: {call_status}')
                return {'call_status': call_status}
            else:
                print(f'Ignoring non-status update message. Message Type: {message_type}')
                return {'message': f'Ignored non-status update. Message Type: {message_type}'}
        else:
            print('No JSON data in the request')
            return {'message': 'No JSON data in the request'}
    except Exception as e:
        print(f"Error handling status update: {str(e)}")
        return {'error': str(e)}
 

async def handle_status_update(message):
    # Handle status updates, e.g., check the 'status' field in the message
    status = message.get('status', '')
    print(f"Received status update: {status}")
    if status == 'ended':
        # Do something when the call has ended
        pass

async def handle_end_of_call_report(message):
    # Handle end-of-call reports, e.g., check 'endedReason' and 'transcript'
    ended_reason = message.get('endedReason', '')
    transcript = message.get('transcript', '')
    print(f"Received end-of-call report. Ended Reason: {ended_reason}, Transcript: {transcript}")
    # Perform actions based on the end-of-call report

if __name__ == '__main__':
    app.run(debug=True)
