import requests
import sys

def fixed_requests_demo():
    url = "https://httpbin.org/delay/10"
    timeout = 3
    
    try:
        print(f"Запрос к {url} (таймаут {timeout} сек)...")
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()  # Проверка HTTP статуса
        
        try:
            data = r.json()
            print(f"OK: {data.get('url')}")
        except requests.exceptions.JSONDecodeError:
            print("ERROR: Ответ не является JSON")
            
    except requests.exceptions.Timeout:
        print(f"ERROR: Таймаут {timeout} сек - сервер слишком медленный")
    except requests.exceptions.ConnectionError:
        print("ERROR: Нет соединения с сервером")
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP ошибка {e.response.status_code}")
    except Exception as e:
        print(f"ERROR: Неизвестная ошибка: {type(e).__name__}: {e}")

if __name__ == "__main__":
    fixed_requests_demo()