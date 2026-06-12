import pandas as pd
from io import StringIO

print("=== Часть 0: Диагностика ===\n")

# ИСПРАВЛЕННЫЙ код
csv_text = "id;value\n1;10\n2;20\n3;30\n"
df = pd.read_csv(StringIO(csv_text), sep=";")

print("1. Исправленный CSV (sep=';'):")
print(df.head())
print(f"\nТипы данных:\n{df.dtypes}")
print(f"\nСреднее value: {df['value'].mean()}")

# Тест 1
csv_text_2 = "id;value\n1;10\n\n3;30\n"
df2 = pd.read_csv(StringIO(csv_text_2), sep=";")
print(f"\n=== Тест 1 (пустая строка) ===")
print(f"Строк: {len(df2)}")
print(df2)

# Тест 2
csv_text_3 = "id;value\n1;10\n2;\n3;30\n"
df3 = pd.read_csv(StringIO(csv_text_3), sep=";")
print(f"\n=== Тест 2 (пропуск в value) ===")
print(df3)
print(f"Тип value: {df3['value'].dtype}")
print(f"Среднее (NaN игнорируется): {df3['value'].mean()}")