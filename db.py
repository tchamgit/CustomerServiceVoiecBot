import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
ALLOWED_LANGUAGES = {'en', 'fr', 'de'}

def create_table(conn):
    try:
        cursor = conn.cursor()
        table_creation_query = '''
            CREATE TABLE IF NOT EXISTS calls (
                call_id VARCHAR(255) PRIMARY KEY,
                first_name VARCHAR(255),
                phone_number VARCHAR(20),
                status VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        prompts_table_creation_query = '''
            CREATE TABLE IF NOT EXISTS prompts (
                id SERIAL PRIMARY KEY,
                prompt_name VARCHAR(255) UNIQUE NOT NULL,
                language VARCHAR(50) NOT NULL,
                first_message TEXT NOT NULL,
                prompt TEXT NOT NULL,
                UNIQUE(prompt_name, language)
            )
        '''
        cursor.execute(table_creation_query)
        cursor.execute(prompts_table_creation_query)
        conn.commit()
        print("Table 'calls' created or already exists.")
    except Exception as e:
        print(f"Error creating table: {str(e)}")

def create_connection():
    dbname = f"{os.getenv('DB_NAME')}"
    user =  f"{os.getenv('DB_USER')}"
    password = f"{os.getenv('DB_PASSWORD')}"
    host = f"{os.getenv('DB_HOST')}"
    port = f"{os.getenv('DB_PORT')}"

    connection_string = f"dbname={dbname} user={user} password={password} host={host} port={port}"

    try:
        conn = psycopg2.connect(connection_string)
        print("Connected to the database")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {str(e)}")
        return None



def save_call_information(call_id, first_name, phone_number, status):
    try:
        conn = create_connection()
        create_table(conn)
        cursor = conn.cursor()
        sql_statement = '''
            INSERT INTO calls (call_id, first_name, phone_number, status, timestamp)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (call_id) DO UPDATE
            SET first_name = EXCLUDED.first_name,
                phone_number = EXCLUDED.phone_number,
                status = EXCLUDED.status,
                timestamp = CURRENT_TIMESTAMP
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
        sql_statement = 'SELECT status FROM calls WHERE call_id = %s'
        cursor.execute(sql_statement, (call_id,))
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
    finally:
        conn.close()


def save_settings(prompt_name, language, first_message, prompt):
    if language not in ALLOWED_LANGUAGES:
        raise ValueError(f"Language {language} is not allowed. Allowed languages are: {', '.join(ALLOWED_LANGUAGES)}")
    try:
        conn = create_connection()
        create_table(conn)
        cursor = conn.cursor()
        sql_statement = '''
            INSERT INTO prompts (prompt_name, language, first_message, prompt)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (prompt_name, language) DO UPDATE
            SET first_message = EXCLUDED.first_message,
                prompt = EXCLUDED.prompt
        '''
        cursor.execute(sql_statement, (prompt_name, language, first_message, prompt))
        conn.commit()
        print(f"Settings saved for prompt: {prompt_name} in {language}")
    except Exception as e:
        print(f"Error saving settings: {str(e)}")
    finally:
        if conn:
            conn.close()

async def update_settings(prompt_name, first_message, prompt):
    if first_message is None and prompt is None:
        raise ValueError("At least one of first_message or prompt must be provided")

    try:
        conn = create_connection()
        create_table(conn)
        cursor = conn.cursor()

        updates = []
        params = []

        if first_message is not None:
            updates.append("first_message = %s")
            params.append(first_message)

        if prompt is not None:
            updates.append("prompt = %s")
            params.append(prompt)

        sql_statement = f'''
            UPDATE prompts
            SET {', '.join(updates)}
            WHERE prompt_name = %s
        '''

        params.extend([prompt_name,])
        cursor.execute(sql_statement, tuple(params))
        conn.commit()
        print(f"Settings updated for prompt: {prompt_name}")
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
    finally:
        if conn:
            conn.close()



async def get_settings(prompt_name):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        sql_statement = 'SELECT prompt_name, language, first_message, prompt FROM prompts WHERE prompt_name = %s'
        cursor.execute(sql_statement, (prompt_name,))
        result = cursor.fetchone()
        if result:
            return {
                "prompt_name": result[0],
                "language": result[1],
                "first_message": result[2],
                "prompt": result[3],
            }
        else:
            print(f"No settings found for prompt: {prompt_name}")
            return None
    except Exception as e:
        print(f"Error getting settings: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()