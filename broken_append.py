import pandas as pd
import os

print("=== Часть 0: Диагностика проблемы append ===\n")

# Удаляем файл перед тестом
if os.path.exists("out.csv"):
    os.remove("out.csv")

print("Первый запуск:")
df = pd.DataFrame({"id": [1, 2], "v": [10, 20]})
df.to_csv("out.csv", mode="a", header=False, index=False)
df_read = pd.read_csv("out.csv", names=["id", "v"])
print(f"Строк в out.csv: {len(df_read)}")
print(df_read)

print("\nВторой запуск (те же данные):")
df.to_csv("out.csv", mode="a", header=False, index=False)
df_read = pd.read_csv("out.csv", names=["id", "v"])
print(f"Строк в out.csv: {len(df_read)}")
print(df_read)

print("\n=== ПРОБЛЕМА ===")
print("При каждом запуске строки удваиваются, хотя данные те же")
print("Нарушение идемпотентности: 2 запуска -> 4 строки")

print("\n=== ИСПРАВЛЕНИЕ (перезапись) ===")
df.to_csv("out_fixed.csv", mode="w", header=False, index=False)
print("Первый запуск: 2 строки")
df.to_csv("out_fixed.csv", mode="w", header=False, index=False)
print("Второй запуск: всё ещё 2 строки (перезапись)")

df_fixed = pd.read_csv("out_fixed.csv", names=["id", "v"])
print(f"Строк: {len(df_fixed)}")

# Очистка
os.remove("out.csv")
os.remove("out_fixed.csv")

print("\n=== Объяснение ===")
print("Проблема: mode='a' (append) добавляет строки без проверки")
print("Решение: mode='w' (перезапись) или дедупликация по ключу")

input("\nНажмите Enter для выхода...")