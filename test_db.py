import sqlite3
import os

def check_database(db_path):
    # 데이터베이스 파일이 존재하는지 확인
    if not os.path.exists(db_path):
        print(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
        return

    # 데이터베이스에 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 목록 조회
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if not tables:
        print("데이터베이스에 테이블이 없습니다.")
    else:
        print("데이터베이스에 존재하는 테이블 목록:")
        for table in tables:
            print(f"- {table[0]}")

            # 각 테이블의 내용 출력
            cursor.execute(f"SELECT * FROM {table[0]};")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(row)
            else:
                print("  (테이블이 비어 있습니다)")

    # 연결 종료
    conn.close()

# 데이터베이스 경로 설정
db_path = os.path.join(os.path.dirname(__file__), 'database', 'database.db')

# 데이터베이스 확인
check_database(db_path)