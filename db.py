yimport os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

def create_table(conn):
    try:
        cursor = conn.cursor()
        table_creation_query = '''
            CREATE TABLE IF NOT EXISTS calls (
                call_id VARCHAR(255) PRIMARY KEY,
                first_name VARCHAR(255),
                phone_number VARCHAR(20),
                status VARCHAR(50)
            )
        '''
        cursor.execute(table_creation_query)
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
            INSERT INTO calls (call_id, first_name, phone_number, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (call_id) DO UPDATE
            SET first_name = EXCLUDED.first_name,
                phone_number = EXCLUDED.phone_number,
                status = EXCLUDED.status
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
