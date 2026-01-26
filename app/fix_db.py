import sqlite3

# Подключаемся к базе
con = sqlite3.connect("coffee_shop.db")
cur = con.cursor()

try:
    # Добавляем колонку shift_type
    cur.execute("ALTER TABLE shifts ADD COLUMN shift_type TEXT DEFAULT 'full'")
    con.commit()
    print("✅ УСПЕШНО! Колонка 'shift_type' добавлена.")
except Exception as e:
    print(f"⚠️ Ошибка (возможно, колонка уже есть): {e}")

con.close()