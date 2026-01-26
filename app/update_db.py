import sqlite3

con = sqlite3.connect("coffee_shop.db")
cur = con.cursor()

try:
    cur.execute("ALTER TABLE extra_tasks ADD COLUMN deadline TIMESTAMP")
    con.commit()
    print("✅ Успешно! Колонка deadline добавлена.")
except Exception as e:
    print(f"⚠️ Колонка уже существует или ошибка: {e}")

con.close()