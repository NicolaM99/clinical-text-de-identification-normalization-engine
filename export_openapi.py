import json
import sys
import os

# Ensure the workspace directory is in the import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app

def generate_openapi():
    print("Generating OpenAPI schema from FastAPI...")
    
    # Retrieve the OpenAPI schema dictionary
    # FastAPI automatically generates the schema based on Pydantic models and endpoint definitions
    openapi_schema = app.openapi()
    
    # Define target path
    output_file = "openapi.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"Successfully exported OpenAPI schema to: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    generate_openapi()
