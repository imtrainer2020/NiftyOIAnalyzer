import requests # type: ignore

response = requests.get('https://www.httpbin.com/get', timeout=30)
print(response.status_code)