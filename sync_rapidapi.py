import os
import sys
import json
import httpx

def sync_definition():
    api_id = os.environ.get("RAPIDAPI_ACCOUNT_ID")
    api_key = os.environ.get("RAPIDAPI_ACCESS_KEY")
    
    if not api_id or not api_key:
        print("Error: RAPIDAPI_ACCOUNT_ID or RAPIDAPI_ACCESS_KEY environment variables not set.")
        sys.exit(1)
        
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "platformv.p.rapidapi.com"
    }
    
    # Step 1: Query the Platform API for versions of this API
    versions_url = f"https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions"
    print(f"Querying API versions from: {versions_url}")
    
    try:
        with httpx.Client(headers=headers, timeout=15.0) as client:
            r = client.get(versions_url)
            if r.status_code != 200:
                print(f"Failed to fetch versions (HTTP {r.status_code}): {r.text}")
                sys.exit(1)
                
            versions_data = r.json()
            print("Received versions data:", json.dumps(versions_data, indent=2))
            
            # Dynamically extract version ID
            version_id = None
            if isinstance(versions_data, list) and len(versions_data) > 0:
                version_id = versions_data[0].get("id")
            elif isinstance(versions_data, dict):
                # Check for list properties in JSON dict
                for key in ["data", "results", "versions"]:
                    if isinstance(versions_data.get(key), list) and len(versions_data[key]) > 0:
                        version_id = versions_data[key][0].get("id")
                        break
                if not version_id:
                    version_id = versions_data.get("id")
                    
            if not version_id:
                print("Could not find a valid version ID in the response.")
                sys.exit(1)
                
            print(f"Targeting active Version ID: {version_id}")
            
            # Step 2: Upload the OpenAPI specification file
            upload_url = f"https://platformv.p.rapidapi.com/v1/apis/{api_id}/versions/{version_id}"
            print(f"Uploading OpenAPI specification to: {upload_url}")
            
            files = {
                "file": ("openapi.json", open("openapi.json", "rb"), "application/json")
            }
            data = {
                "fileFormat": "oas"
            }
            
            # Execute PUT request as multipart/form-data
            r_upload = client.put(upload_url, files=files, data=data)
            if r_upload.status_code in [200, 201, 204]:
                print("Successfully synchronized OpenAPI definition with RapidAPI!")
            else:
                print(f"Failed to upload definition (HTTP {r_upload.status_code}): {r_upload.text}")
                sys.exit(1)
                
    except Exception as e:
        print(f"An unexpected error occurred during synchronization: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    sync_definition()
