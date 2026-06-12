import pandas as pd

print("=== Часть 0: Диагностика many-to-many merge ===\n")

# Исходные данные
left = pd.DataFrame({
    "id": [1, 1, 2],
    "value": [10, 11, 20]
})

right = pd.DataFrame({
    "id": [1, 1, 2],
    "name": ["A", "A_dup", "B"]
})

print("left:")
print(left)
print(f"\nright (грязный справочник):")
print(right)

# ПРОБЛЕМА: many-to-many
merged = left.merge(right, on="id", how="left")
print(f"\n=== ПРОБЛЕМА ===")
print(f"Было строк: {len(left)} -> Стало: {len(merged)}")
print(merged)

# ИСПРАВЛЕНИЕ 1: очистка справочника от дубликатов
right_clean = right.drop_duplicates(subset=["id"])
merged_clean = left.merge(right_clean, on="id", how="left")
print(f"\n=== ИСПРАВЛЕНИЕ 1 (drop_duplicates) ===")
print(f"Было: {len(left)} -> Стало: {len(merged_clean)}")
print(merged_clean)

# ИСПРАВЛЕНИЕ 2: проверка кардинальности
print(f"\n=== ИСПРАВЛЕНИЕ 2 (validate) ===")
try:
    left.merge(right, on="id", how="left", validate="many_to_one")
except Exception as e:
    print(f"Ошибка: {e}")

print("\n=== Объяснение ===")
print("Проблема: id=1 встречается 2 раза слева и 2 раза справа")
print("Результат: 2 x 2 = 4 строки для id=1")
print("Опасность: искажаются суммы, средние и count метрики")