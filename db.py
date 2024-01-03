import sqlite3

def create_connection():
    return sqlite3.connect('relight.db')

def save_call_information(call_id, first_name, phone_number, status):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        sql_statement = '''
            INSERT OR REPLACE INTO calls (call_id, first_name, phone_number, status)
            VALUES (?, ?, ?, ?)
        '''
        print("Executing SQL:", sql_statement)
        cursor.execute(sql_statement, (call_id, first_name, phone_number, status))
        conn.commit()
        print(f"Call information saved: Call ID - {call_id}, Status - {status}")
    except Exception as e:
        print(f"Error saving call information: {str(e)}")
    finally:
        conn.close()



def get_existing_status(call_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM calls WHERE call_id = ?', (call_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        print(f"Error getting existing status: {str(e)}")
        return None


async def get_all_calls():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM calls')
        result = cursor.fetchall()
        if result:
            column_names = [desc[0] for desc in cursor.description]
            calls_data = [dict(zip(column_names, row)) for row in result]
            return calls_data
        else:
            return None
    except Exception as e:
        print(f"Error getting existing status: {str(e)}")
        return None
