# Clinical Text De-Identification & Normalization Engine

A high-performance, production-ready, serverless-optimized API designed for the sanitization, abbreviation expansion, and boundary-aware chunking of raw, unstructured clinical notes. This engine is designed to prevent data leakage of Protected Health Information (PHI) and normalize shorthand clinical jargon, making it an ideal pre-processing step for downstream RAG (Retrieval-Augmented Generation) pipelines, LLMs, or medical vector databases.

---

## Technical Architecture & Optimization

- **Zero-Cold-Start Philosophy**: Replaces heavy SpaCy, HuggingFace, or transformer models with pre-compiled, optimized regular expressions and in-memory key-value lookups.
- **Fast Execution**: Average response time under **10ms** (excluding network transit).
- **Extremely Low Memory Footprint**: Runs comfortably below **50MB RAM** (limit is 256MB on serverless runtimes).
- **Cloud-Native Integration**: Equipped with an ASGI adapter (`Mangum`) out-of-the-box for seamless deployments on AWS Lambda, Google Cloud Functions, or any ASGI/WSGI gateway.

---

## API Documentation

### POST `/api/v1/clinical-sanitize`

Processes a raw clinical note to de-identify PII/PHI, normalize standard abbreviations, and chunk the text.

#### Request Schema

- **Headers**: `Content-Type: application/json`
- **Body**:

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `clinical_note` | `string` | **Yes** | — | Raw, unstructured clinical text. |
| `max_tokens` | `integer` | No | `500` | Maximum character length of each structural text chunk. Range: `50` to `5000`. |

```json
{
  "clinical_note": "Patient: John Doe, 45yo male, presented to Boston Medical Center on 10/12/2021. SSN: 000-12-3456. Complaining of SOB.",
  "max_tokens": 500
}
```

#### Response Schema

Returns a JSON object detailing status, processing metadata, the full sanitized/normalized text, a list of normalized abbreviations found, and boundary-aware chunks.

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

## Serverless Deployment Guide

### 1. Google Cloud Functions (Python Runtime)

Google Cloud Functions supports FastAPI natively via standard WSGI/ASGI servers (functions-framework).

1. Zip your project files:
   ```bash
   zip -r function.zip main.py requirements.txt
   ```
2. Deploy using the `gcloud` CLI:
   ```bash
   gcloud functions deploy clinical-sanitize-engine \
     --runtime python310 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point app \
     --memory 256MB
   ```
   *Note: Set `--entry-point app` since FastAPI's `app` is exposed directly in `main.py`.*

### 2. AWS Lambda (via API Gateway or Function URLs)

AWS Lambda executes ASGI applications using the Mangum handler exposed as `handler` in `main.py`.

1. Package the application and dependencies:
   ```bash
   pip install -r requirements.txt -t lib
   cd lib && zip -r ../deployment_package.zip . && cd ..
   zip -g deployment_package.zip main.py
   ```
2. Deploy the `deployment_package.zip` to AWS Lambda.
3. Configure the Lambda handler to: `main.handler`.
4. Add an **API Gateway (HTTP API)** trigger or enable **Function URLs** to route traffic.

---

## Monetization on RapidAPI

### Step-by-Step RapidAPI Setup

1. **Create a Developer Account**: Sign up at [RapidAPI Provider Portal](https://rapidapi.com/studio).
2. **Add New API**:
   - **API Name**: `Clinical Text De-Identification & Normalization Engine`
   - **Short Description**: `PII/PHI de-identification and clinical abbreviation expansion tool, optimized for serverless RAG ingestion pipelines.`
   - **Category**: `Medical / Health`
3. **Configure Gateway/Target URL**:
   - Point the **Target URL** to your Google Cloud Function URL or AWS Lambda Function URL/API Gateway URL (e.g. `https://<your-lambda-id>.execute-api.us-east-1.amazonaws.com`).
4. **Define REST Endpoints**:
   - Add a POST endpoint `/api/v1/clinical-sanitize`.
   - Add request body parameter schema using the JSON schema provided in the API documentation section.
5. **Configure Subscription & Pricing Plans**:
   - **Basic**: 100 free requests/month (with rate limiting).
   - **Pro**: $19/month for 5,000 requests.
   - **Ultra**: $79/month for 50,000 requests.
   - **Mega**: $199/month for 200,000 requests.
6. **Publish**: Save changes and set the API status to **Public**.

---

*Note: OpenAPI documentation is automatically synced with RapidAPI on every push to the main branch.*
