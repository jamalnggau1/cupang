import sqlite3

def create_connection():
    connection = sqlite3.connect("chatbot.db")
    return connection

def create_table():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            gender TEXT,
            language TEXT
        )
    ''')
    connection.commit()
    connection.close()

create_table()