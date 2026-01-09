import sqlite3
import os

def check_table_structure():
    db_path = os.path.join(os.path.dirname(__file__), 'guiConfigs', 'guiNDB.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查ProfileItem表结构
    cursor.execute('PRAGMA table_info(ProfileItem)')
    columns = cursor.fetchall()
    
    print('ProfileItem表结构:')
    for col in columns:
        print(f'{col[1]} ({col[2]}) - PK: {col[5]}')
    
    # 检查现有数据
    cursor.execute('SELECT * FROM ProfileItem LIMIT 1')
    row = cursor.fetchone()
    if row:
        print('\n示例数据:')
        for i, value in enumerate(row):
            print(f'{columns[i][1]}: {value}')
    
    conn.close()

if __name__ == "__main__":
    check_table_structure()