import sqlite3
import os

print("=== Часть 0: Диагностика транзакций ===\n")

db_path = "example.db"
print("db file:", os.path.abspath(db_path))

# Проблемный код (без commit)
con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS t(x int);")
con.commit()

cur.execute("DELETE FROM t;")
con.commit()

cur.execute("INSERT INTO t(x) VALUES (1);")
# BUG: забыли con.commit()

con.close()

# Проверяем сохранились ли данные
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM t;")
print("COUNT без commit:", cur.fetchone()[0])
con.close()

# ИСПРАВЛЕННЫЙ код (с commit)
print("\n=== Исправленный код (с commit) ===")

con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("DELETE FROM t;")
con.commit()

cur.execute("INSERT INTO t(x) VALUES (1);")
con.commit()  # <- исправление

con.close()

con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM t;")
print("COUNT с commit:", cur.fetchone()[0])
con.close()

# Очистка
os.remove(db_path)

print("\n=== Объяснение ===")
print("Без commit() изменения не переживают закрытие соединения")
print("В PostgreSQL with engine.begin() делает commit автоматически")
input("\nНажмите Enter для выхода...")