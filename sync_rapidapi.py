import os
import sys
import httpx

def test_sync():
    api_id = os.environ.get("RAPIDAPI_ACCOUNT_ID")
    api_key = os.environ.get("RAPIDAPI_ACCESS_KEY")
    version_id = "apiversion_e1a4947d-bd49-497a-9c68-a199f7adb83f"
    
    scenarios = [
        ("https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions", "platformv.p.rapidapi.com"),
        ("https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions/{version_id}", "platformv.p.rapidapi.com"),
        ("https://platform.rapidapi.com/v1/apis/{api_id}/versions", "platform.rapidapi.com"),
        ("https://platform.rapidapi.com/v1/apis/{api_id}/versions/{version_id}", "platform.rapidapi.com"),
        ("https://platform-api.rapidapi.com/v1/apis/{api_id}/versions", "platform-api.rapidapi.com"),
        ("https://platform-api.rapidapi.com/v1/apis/{api_id}/versions/{version_id}", "platform-api.rapidapi.com"),
        ("https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions", "platformapi1.rapidapi-x.rapidapi.com"),
        ("https://rest-platform-api.p.rapidapi.com/v1/apis/{api_id}/versions", "rest-platform-api.p.rapidapi.com"),
    ]
    
    print(f"API ID being tested: {api_id}")
    
    for url_template, host in scenarios:
        url = url_template.format(api_id=api_id, version_id=version_id)
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host
        }
        try:
            r = httpx.get(url, headers=headers, timeout=10.0)
            print(f"URL: {url} | Host: {host} -> HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"URL: {url} | Host: {host} failed: {e}")

if __name__ == "__main__":
    test_sync()
