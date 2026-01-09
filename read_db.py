import sqlite3
import json
import os
import base64
import re

def read_database():
    db_path = os.path.join(os.path.dirname(__file__), 'guiConfigs', 'guiNDB.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("数据库表结构:")
    for table in tables:
        table_name = table[0]
        print(f"\n表名: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("列信息:")
        for col in columns:
            print(f"  {col}")
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        rows = cursor.fetchall()
        if rows:
            print(f"示例数据 (前5行):")
            for row in rows:
                print(f"  {row}")
    
    conn.close()

if __name__ == "__main__":
    read_database()
