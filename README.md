# Clinical Text De-Identification & Normalization Engine 🩺🔒

[![License: MIT](https://img.shields.io/github/license/NicolaM99/clinical-text-de-identification-normalization-engine?style=flat-square&color=blue)](LICENSE)
[![CI/CD Sync](https://img.shields.io/github/actions/workflow/status/NicolaM99/clinical-text-de-identification-normalization-engine/rapidapi-sync.yml?branch=main&label=RapidAPI%20Sync&style=flat-square)](https://github.com/NicolaM99/clinical-text-de-identification-normalization-engine/actions)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.13-brightgreen?style=flat-square)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Cloud Run](https://img.shields.io/badge/GCP%20Cloud%20Run-Deployed-blue?style=flat-square&logo=google-cloud&logoColor=white)](#)

An ultra-fast, serverless-optimized, and production-ready Clinical NLP engine. It is designed specifically for sanitizing, expanding abbreviations, and chunking raw, unstructured clinical notes. This engine acts as a secure pre-processing gateway for downstream Retrieval-Augmented Generation (RAG) pipelines, LLMs, or medical vector databases, preventing the leakage of Protected Health Information (PHI) to third-party AI models.

---

## 🚀 Key Features

- **Zero-Cold-Start Architecture**: Replaces heavy neural models (SpaCy, HuggingFace, transformers) with highly optimized, pre-compiled regular expressions and in-memory key-value lookups.
- **Ultra-Low Latency**: Processes notes and redacts data with an average execution time under **10ms** (excluding network transit).
- **HIPAA & MIMIC-III Compliance**: Redacts names, dates, SSNs, Italian Tax IDs (Codice Fiscale), hospital names, and contact details into standard tokens (e.g., `[REDACTED_NAME]`, `[REDACTED_DATE]`).
- **Medical Abbreviation Expansion**: Automatically normalizes standard shorthand clinical jargon in-memory (e.g., `HTN` -> `hypertension`, `BID` -> `twice a day`).
- **Boundary-Aware Chunking**: Structurally chunks text respecting paragraph and sentence boundaries below user-defined limits (e.g., `max_tokens=500`).
- **Cloud Native**: Out-of-the-box support for AWS Lambda (via `Mangum`) and Google Cloud Run.

---

## 📋 Table of Contents

- [Clinical Abbreviation Reference](#-clinical-abbreviation-reference)
- [Local Development & Setup](#-local-development--setup)
- [API Documentation](#-api-documentation)
- [Client Integration Examples](#-client-integration-examples)
- [Serverless Deployment Guide](#-serverless-deployment-guide)
- [License](#-license)

---

## 🩺 Clinical Abbreviation Reference

The engine normalizes 28+ clinical shorthands dynamically during text processing:

| Abbreviation | Expanded Definition | Category |
|---|---|---|
| `HTN` | hypertension | Condition |
| `DM` | diabetes mellitus | Condition |
| `CAD` | coronary artery disease | Condition |
| `CHF` | congestive heart failure | Condition |
| `CKD` | chronic kidney disease | Condition |
| `COPD` | chronic obstructive pulmonary disease | Condition |
| `BID` | twice a day | Dosage Frequency |
| `QD` | once a day | Dosage Frequency |
| `QHS` | at bedtime | Dosage Frequency |
| `PRN` | as needed | Dosage Frequency |
| `SOB` | shortness of breath | Symptom |
| `Dx` / `Tx` / `Rx` / `Hx` | diagnosis / treatment / prescription / history | Clinical Process |

---

## 💻 Local Development & Setup

### Prerequisites
- Python 3.11 or 3.13
- Pip (Python Package Manager)

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/NicolaM99/clinical-text-de-identification-normalization-engine.git
cd clinical-text-de-identification-normalization-engine
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Local Development Server
Spin up the FastAPI server using Uvicorn:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Access the interactive OpenAPI swagger documentation at `http://127.0.0.1:8000/docs`.

### 3. Run Benchmarks & Stress Tests
Execute the concurrent asynchronous stress-testing suite:
```bash
python stress_test.py
```
This script generates 50 synthetic medical notes, fires them concurrently via `httpx`, executes assertions on correctness, and outputs performance statistics.

---

## 📡 API Documentation

### POST `/api/v1/clinical-sanitize`
Sanitizes a clinical note by removing PII/PHI, expanding abbreviations, and chunking the resulting text.

#### Request Headers
- `Content-Type: application/json`

#### Request Body
- `clinical_note` (string, Required): The raw clinical text.
- `max_tokens` (integer, Optional, Default: `500`): Maximum character length per chunk. Range: `50` to `5000`.

*Request JSON Example:*
```json
{
  "clinical_note": "Patient: John Doe, 45yo male, presented to Boston Medical Center on 10/12/2021. SSN: 000-12-3456. Complaining of SOB.",
  "max_tokens": 500
}
```

#### Response Body
- `status` (string): Operation outcome (`success`).
- `metadata` (object): Statistics detailing characters processed and chunks created.
- `sanitized_text` (string): The completely sanitized and expanded medical text.
- `normalized_terms_found` (array of strings): Abbreviation acronyms detected and expanded.
- `chunks` (array of objects): Boundary-aware text splits for embedding/RAG.

*Response JSON Example:*
```json
{
  "status": "success",
  "metadata": {
    "processed_chars": 111,
    "chunks_count": 1
  },
  "sanitized_text": "Patient: [REDACTED_NAME], 45yo male, presented to [REDACTED_HOSPITAL] on [REDACTED_DATE]. SSN: [REDACTED_ID]. Complaining of shortness of breath.",
  "normalized_terms_found": [
    "SOB"
  ],
  "chunks": [
    {
      "chunk_id": 1,
      "text": "Patient: [REDACTED_NAME], 45yo male, presented to [REDACTED_HOSPITAL] on [REDACTED_DATE]. SSN: [REDACTED_ID]. Complaining of shortness of breath."
    }
  ]
}
```

---

## 🛠️ Client Integration Examples

### cURL
```bash
curl --request POST \
  --url https://clinical-sanitizer-api-731921218341.europe-west1.run.app/api/v1/clinical-sanitize \
  --header 'Content-Type: application/json' \
  --data '{
    "clinical_note": "Patient John Doe, presenting with HTN and DM.",
    "max_tokens": 500
  }'
```

### Python (httpx)
```python
import httpx

url = "https://clinical-sanitizer-api-731921218341.europe-west1.run.app/api/v1/clinical-sanitize"
payload = {
    "clinical_note": "Patient John Doe, presenting with HTN and DM.",
    "max_tokens": 500
}

with httpx.Client() as client:
    response = client.post(url, json=payload)
    print(response.json())
```

### JavaScript (Axios)
```javascript
const axios = require('axios');

const options = {
  method: 'POST',
  url: 'https://clinical-sanitizer-api-731921218341.europe-west1.run.app/api/v1/clinical-sanitize',
  headers: {'Content-Type': 'application/json'},
  data: {
    clinical_note: 'Patient John Doe, presenting with HTN and DM.',
    max_tokens: 500
  }
};

axios.request(options).then((response) => {
  console.log(response.data);
}).catch((error) => {
  console.error(error);
});
```

---

## ☁️ Serverless Deployment Guide

### 1. Google Cloud Run (via Cloud Buildpacks)
Our repository is fully optimized for GCP Cloud Buildpacks deployment using Python 3.13. Build settings are managed dynamically via `project.toml`.

To deploy, simply link your repository to Google Cloud Run and configure build triggers on pushes to the `main` branch.

### 2. AWS Lambda
FastAPI applications run seamlessly on AWS Lambda using the pre-configured Mangum ASGI adapter:
1. Package dependencies:
   ```bash
   pip install -r requirements.txt -t lib
   cd lib && zip -r ../deployment_package.zip . && cd ..
   zip -g deployment_package.zip main.py
   ```
2. Upload the `deployment_package.zip` to your AWS Lambda function.
3. Set the Lambda Handler entrypoint to: `main.handler`.

---

## ⚖️ License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information. 
