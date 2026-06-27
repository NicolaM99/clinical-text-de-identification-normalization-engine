import os
import sys
import time
import httpx

def sync_definition():
    api_id = os.environ.get("RAPIDAPI_ACCOUNT_ID")
    api_key = os.environ.get("RAPIDAPI_ACCESS_KEY")
    version_id = os.environ.get("RAPIDAPI_VERSION_ID")
    
    if not api_id or not api_key or not version_id:
        print("Error: RAPIDAPI_ACCOUNT_ID, RAPIDAPI_ACCESS_KEY, or RAPIDAPI_VERSION_ID environment variables not set.")
        sys.exit(1)
        
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "platformv.p.rapidapi.com"
    }
    
    upload_url = f"https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions/{version_id}"
    print(f"Uploading OpenAPI specification directly to: {upload_url}")
    
    # Define retry parameters for handling HTTP 429 rate limiting
    max_retries = 5
    backoff_time = 2.0  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            # Re-open file on each retry
            files = {
                "file": ("openapi.json", open("openapi.json", "rb"), "application/json")
            }
            data = {
                "fileFormat": "oas"
            }
            
            with httpx.Client(headers=headers, timeout=20.0) as client:
                r_upload = client.put(upload_url, files=files, data=data)
                
                if r_upload.status_code in [200, 201, 204]:
                    print("Successfully synchronized OpenAPI definition with RapidAPI!")
                    sys.exit(0)
                elif r_upload.status_code == 429:
                    print(f"[Attempt {attempt}/{max_retries}] Received HTTP 429 (Too many requests). Backing off for {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time *= 2.0  # Exponential increase
                else:
                    print(f"Failed to upload definition (HTTP {r_upload.status_code}): {r_upload.text}")
                    sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred on attempt {attempt}: {str(e)}")
            if attempt == max_retries:
                sys.exit(1)
            time.sleep(backoff_time)
            backoff_time *= 2.0

    print("Failed to sync definition after maximum retries due to rate limiting.")
    sys.exit(1)

if __name__ == "__main__":
    sync_definition()
