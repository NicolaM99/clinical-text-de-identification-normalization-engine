import re
import time
import logging
import json
from typing import List, Optional, Tuple
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from mangum import Mangum

# --- Structured Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clinical-sanitize-engine")

def log_info(event: str, details: dict):
    logger.info(json.dumps({"event": event, "timestamp": time.time(), **details}))

def log_error(event: str, details: dict):
    logger.error(json.dumps({"event": event, "timestamp": time.time(), **details}))


# --- Pydantic Schemas ---
class ClinicalSanitizeRequest(BaseModel):
    clinical_note: str = Field(
        ..., 
        description="Raw, unstructured clinical note to be de-identified and normalized.",
        examples=["Patient: John Doe, 45yo male, presented to Boston Medical Center on 10/12/2021. SSN: 000-12-3456. Complaining of SOB."]
    )
    max_tokens: Optional[int] = Field(
        500, 
        description="Maximum character length for each structural chunk.", 
        ge=50, 
        le=5000
    )


class ChunkItem(BaseModel):
    chunk_id: int = Field(..., description="Sequential index of the chunk.")
    text: str = Field(..., description="Sanitized and normalized text snippet of the chunk.")


class MetadataInfo(BaseModel):
    processed_chars: int = Field(..., description="Total characters processed from the input note.")
    chunks_count: int = Field(..., description="Total number of chunks generated.")


class ClinicalSanitizeResponse(BaseModel):
    status: str = Field("success", description="Status of the operation.")
    metadata: MetadataInfo = Field(..., description="Execution metadata.")
    sanitized_text: str = Field(..., description="Entire sanitized and normalized text.")
    normalized_terms_found: List[str] = Field(..., description="Unique medical abbreviations normalized during processing.")
    chunks: List[ChunkItem] = Field(..., description="List of semantic text chunks for downstream RAG pipeline ingestion.")


# --- Clinical Processing Engine ---
class ClinicalSanitizer:
    def __init__(self):
        # 1. Clinical Abbreviation Mapping (Case-Insensitive)
        self.abbrev_map = {
            r"\bb\.?i\.?d\.?\b": ("twice a day", "bid"),
            r"\bq\.?d\.?\b": ("once a day", "qd"),
            r"\bp\.?r\.?n\.?\b": ("as needed", "PRN"),
            r"\bhtn\b": ("Hypertension", "HTN"),
            r"\bdm\b": ("Diabetes Mellitus", "DM"),
            r"\bt\.?i\.?d\.?\b": ("three times a day", "tid"),
            r"\bq\.?i\.?d\.?\b": ("four times a day", "qid"),
            r"\bp\.?o\.?\b": ("by mouth", "po"),
            r"\bi\.?v\.?\b": ("intravenous", "iv"),
            r"\bi\.?m\.?\b": ("intramuscular", "im"),
            r"\bs\.?c\.?\b": ("subcutaneous", "subq"),
            r"\bsubq\b": ("subcutaneous", "subq"),
            r"\bdx\b": ("diagnosis", "Dx"),
            r"\btx\b": ("treatment", "Tx"),
            r"\brx\b": ("prescription", "Rx"),
            r"\bhx\b": ("history", "Hx"),
            r"\bbp\b": ("blood pressure", "BP"),
            r"\bhr\b": ("heart rate", "HR"),
            r"\bicu\b": ("Intensive Care Unit", "ICU"),
            r"\ber\b": ("Emergency Room", "ER"),
            r"\bsob\b": ("shortness of breath", "SOB"),
            r"\bcad\b": ("Coronary Artery Disease", "CAD"),
            r"\bckd\b": ("Chronic Kidney Disease", "CKD"),
            r"\bcopd\b": ("Chronic Obstructive Pulmonary Disease", "COPD"),
            r"\bgerd\b": ("Gastroesophageal Reflux Disease", "GERD"),
            r"\buti\b": ("Urinary Tract Infection", "UTI"),
            r"\bchf\b": ("Congestive Heart Failure", "CHF"),
            r"\bq\.?h\.?s\.?\b": ("at bedtime", "qhs"),
        }
        
        self.compiled_abbrevs = [
            (re.compile(pattern, re.IGNORECASE), repl, canonical)
            for pattern, (repl, canonical) in self.abbrev_map.items()
        ]
        
        # 2. Pre-compiled De-identification Regexes for maximum performance (<10ms processing)
        # SSN & Codice Fiscale
        self.ssn_re = re.compile(r"\b\d{3}-\d{2,3}-\d{4}\b")
        self.cf_re = re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T][0-9LMNPQRSTV]{2}[A-Z][0-9LMNPQRSTV]{3}[A-Z]\b", re.IGNORECASE)
        
        # Dates (MM/DD/YYYY, YYYY-MM-DD, Month DD YYYY, DD Month YYYY)
        self.date_re1 = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
        self.date_re2 = re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b")
        self.date_re3 = re.compile(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", 
            re.IGNORECASE
        )
        self.date_re4 = re.compile(
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
            re.IGNORECASE
        )
        
        # IDs (MRN, SSN, ID, Patient ID, Record No, etc.)
        self.ids_re = re.compile(
            r"\b(?:MRN|SSN|ID|Patient ID|Record No|No\.|Codice Paziente)\s*[:#-]?\s*[\d-]+\b",
            re.IGNORECASE
        )
        
        # Patient & Doctor names with standard medical titles / prefix labels
        self.names_re = re.compile(
            r"\b(?:Dr\.|Doctor|Mr\.|Mrs\.|Ms\.|Patient|Dr|Physician|Dr\.ssa|Paziente|Medico)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
            re.IGNORECASE
        )
        
        # Hospitals, clinics, and medical centers
        self.hospitals_re = re.compile(
            r"\b[A-Za-z0-9\s']+(?:Hospital|Clinic|Medical Center|Sanatorio|Ospedale|Policlinico|Clinica)\b",
            re.IGNORECASE
        )
        
        # Stray punctuation or dangling symbols (orphan hyphens, dashes, slashes, etc.)
        self.orphan_re = re.compile(r"[ \t]+[-–—_/\\*]{1,3}[ \t]+")

    def de_identify(self, text: str) -> str:
        # Step 1: Mask SSN and Tax ID
        text = self.ssn_re.sub("[REDACTED_ID]", text)
        text = self.cf_re.sub("[REDACTED_ID]", text)
        
        # Step 2: Mask Patient IDs / MRN
        text = self.ids_re.sub("[REDACTED_ID]", text)
        
        # Step 3: Mask Names with prefix syntax (e.g. Patient: John Doe, Doctor: Alice Smith, Physician John Doe)
        text = re.sub(
            r"\b(Patient|Doctor|Physician|Dr\.|Mr\.|Mrs\.|Ms\.|Name|Paziente|Medico|Dr\.ssa)\s*:?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            lambda m: f"{m.group(1)}: [REDACTED_NAME]" if ":" in m.group(0) else f"{m.group(1)} [REDACTED_NAME]",
            text,
            flags=re.IGNORECASE
        )
        
        # Step 4: Mask standard Doctor/Patient names with titles
        text = self.names_re.sub("[REDACTED_NAME]", text)
        
        # Step 5: Mask Dates
        text = self.date_re1.sub("[REDACTED_DATE]", text)
        text = self.date_re2.sub("[REDACTED_DATE]", text)
        text = self.date_re3.sub("[REDACTED_DATE]", text)
        text = self.date_re4.sub("[REDACTED_DATE]", text)
        
        # Step 6: Mask Hospital/Clinic Names
        text = self.hospitals_re.sub("[REDACTED_HOSPITAL]", text)
        
        return text

    def normalize_and_clean(self, text: str) -> Tuple[str, List[str]]:
        found_terms = []
        
        # Apply static abbreviation expansion
        for pattern_re, repl, canonical in self.compiled_abbrevs:
            if pattern_re.search(text):
                found_terms.append(canonical)
                text = pattern_re.sub(repl, text)
                
        # Clean orphan special characters
        text = self.orphan_re.sub(" ", text)
        
        # Normalize double/horizontal spaces but preserve single/double newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Remove any leading/trailing spaces
        text = text.strip()
        
        return text, sorted(list(set(found_terms)))

    def chunk_text(self, text: str, max_chars: int = 500) -> List[ChunkItem]:
        paragraphs = text.split("\n\n")
        units = []
        
        # Break text down into structural units (paragraphs or sentences)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(para) <= max_chars:
                units.append(para)
            else:
                # If paragraph exceeds max_chars, split into sentences
                # Neg lookbehinds to prevent splitting on titles (e.g. Dr., Mr.)
                sentence_end = re.compile(
                    r"(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bProf)(?<!\bvs)(?<!\b[A-Z])(?<=[.!?])\s+"
                )
                sentences = sentence_end.split(para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    if len(sentence) <= max_chars:
                        units.append(sentence)
                    else:
                        # Fallback: if sentence itself is longer than max_chars, split on space
                        words = sentence.split(" ")
                        current_sub = []
                        for word in words:
                            # Check character length
                            if sum(len(w) + 1 for w in current_sub) + len(word) <= max_chars:
                                current_sub.append(word)
                            else:
                                if current_sub:
                                    units.append(" ".join(current_sub))
                                current_sub = [word]
                        if current_sub:
                            units.append(" ".join(current_sub))
        
        # Re-assemble structural units into chunks up to max_chars
        chunks = []
        current_chunk = []
        current_len = 0
        chunk_id = 1
        
        for unit in units:
            unit_len = len(unit)
            separator_len = 1 if current_chunk else 0
            
            if current_len + separator_len + unit_len > max_chars:
                if current_chunk:
                    chunks.append(ChunkItem(
                        chunk_id=chunk_id,
                        text=" ".join(current_chunk)
                    ))
                    chunk_id += 1
                    current_chunk = [unit]
                    current_len = unit_len
                else:
                    # Unit itself is larger than max_chars
                    chunks.append(ChunkItem(
                        chunk_id=chunk_id,
                        text=unit
                    ))
                    chunk_id += 1
            else:
                current_chunk.append(unit)
                current_len += separator_len + unit_len
                
        if current_chunk:
            chunks.append(ChunkItem(
                chunk_id=chunk_id,
                text=" ".join(current_chunk)
            ))
            
        return chunks


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Clinical Text De-Identification & Normalization Engine",
    description="Production-ready serverless API for clinical note processing.",
    version="1.0.0"
)

# Instantiate the engine globally to leverage warm serverless execution contexts
engine = ClinicalSanitizer()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for container probes and API status validation."""
    return {"status": "healthy", "timestamp": time.time()}


@app.post(
    "/api/v1/clinical-sanitize", 
    response_model=ClinicalSanitizeResponse,
    status_code=status.HTTP_200_OK
)
async def sanitize_clinical_text(request: ClinicalSanitizeRequest):
    """
    Asynchronously ingest raw clinical notes, de-identify, normalize, and chunk
    the content for downstream vector indexing and RAG pipeline integration.
    """
    start_time = time.time()
    raw_note = request.clinical_note.strip()
    
    # Validation: reject empty notes
    if not raw_note:
        log_error("validation_failure", {"reason": "Empty clinical_note provided"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The input 'clinical_note' field cannot be empty or whitespace only."
        )
        
    try:
        # Step 1: De-identification (Privacy Masking)
        de_identified_text = engine.de_identify(raw_note)
        
        # Step 2: Clinical Normalization (Abbreviation expansion + orphan symbol cleanup)
        sanitized_text, normalized_terms_found = engine.normalize_and_clean(de_identified_text)
        
        # Step 3: Semantic & Structural Chunking
        chunks = engine.chunk_text(sanitized_text, max_chars=request.max_tokens)
        
        latency_ms = (time.time() - start_time) * 1000
        
        log_info("processing_success", {
            "input_chars": len(raw_note),
            "output_chars": len(sanitized_text),
            "chunks_count": len(chunks),
            "latency_ms": latency_ms
        })
        
        return ClinicalSanitizeResponse(
            status="success",
            metadata=MetadataInfo(
                processed_chars=len(raw_note),
                chunks_count=len(chunks)
            ),
            sanitized_text=sanitized_text,
            normalized_terms_found=normalized_terms_found,
            chunks=chunks
        )
        
    except Exception as e:
        log_error("internal_processing_error", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while processing the clinical note: {str(e)}"
        )


# --- Serverless Handler Adapter ---
# Expose Mangum wrapper to bridge ASGI to AWS Lambda API Gateway / Function URL events.
# For Google Cloud Functions, the FastAPI 'app' instance can be referenced directly.
handler = Mangum(app)
