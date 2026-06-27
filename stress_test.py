import asyncio
import time
import random
import json
import re
import httpx
from typing import List, Dict, Any

# --- Programmatic MIMIC-III Style Dataset Generator ---
def generate_stress_dataset(num_notes: int = 50) -> List[Dict[str, Any]]:
    random.seed(42)  # Deterministic generation for reproducible benchmarks
    
    first_names_it = ["Mario", "Giuseppe", "Elena", "Luigi", "Francesca", "Alessandro", "Giulia", "Roberto"]
    last_names_it = ["Rossi", "Bianchi", "Verdi", "Russo", "Ferrari", "Esposito", "Romano", "Gallo"]
    
    first_names_en = ["John", "Jane", "Alice", "Bob", "Meredith", "Gregory", "Jean-Pierre", "Hans"]
    last_names_en = ["Smith", "Doe", "Grey", "House", "Watson", "Dupont", "Schmidt", "Miller"]
    
    doctors_titles = ["Dr.", "Doctor", "Physician", "Dr.ssa"]
    
    dates_templates = [
        "{day:02d}/{month:02d}/{year:4d}",
        "{year:4d}-{month:02d}-{day:02d}",
        "{month:02d}-{day:02d}-{year:2d}",
        "{month_str} {day:d}, {year:4d}",
        "{day:d} {month_str_short} {year:4d}"
    ]
    
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    months_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    hospitals_prefixes = ["Ospedale", "Policlinico", "Clinica", "Sanatorio"]
    hospitals_suffixes = ["Hospital", "Clinic", "Medical Center", "General Hospital"]
    hospitals_names = ["Umberto I", "San Raffaele", "Gemelli", "Niguarda", "Boston", "St. Jude", "Mayo", "Cleveland"]
    
    abbrevs = {
        "HTN": "Hypertension",
        "DM": "Diabetes Mellitus",
        "COPD": "Chronic Obstructive Pulmonary Disease",
        "GERD": "Gastroesophageal Reflux Disease",
        "CKD": "Chronic Kidney Disease",
        "CAD": "Coronary Artery Disease",
        "CHF": "Congestive Heart Failure",
        "bid": "twice a day",
        "qd": "once a day",
        "prn": "as needed",
        "po": "by mouth",
        "sob": "shortness of breath",
        "qhs": "at bedtime",
        "tid": "three times a day"
    }

    dataset = []
    
    for i in range(num_notes):
        # Generate PII targets
        p_first = random.choice(first_names_it if i % 2 == 0 else first_names_en)
        p_last = random.choice(last_names_it if i % 2 == 0 else last_names_en)
        p_name = f"{p_first} {p_last}"
        
        d_first = random.choice(first_names_en if i % 2 == 0 else first_names_it)
        d_last = random.choice(last_names_en if i % 2 == 0 else last_names_it)
        d_title = random.choice(doctors_titles)
        d_name = f"{d_title} {d_first} {d_last}"
        
        # SSN & Codice Fiscale
        ssn_val = f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"
        cf_val = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6)) + \
                 f"{random.randint(10,99)}" + \
                 random.choice("ABCDEHLMPRST") + \
                 f"{random.randint(10,99)}" + \
                 random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + \
                 f"{random.randint(100,999)}" + \
                 random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
        # Phone
        phone_val = f"+{random.randint(1,99)} {random.randint(100,999)} {random.randint(100000,999999)}"
        
        # Dates
        y, m, d = random.randint(1950, 2026), random.randint(1, 12), random.randint(1, 28)
        dob_template = random.choice(dates_templates)
        dob_str = dob_template.format(
            day=d, month=m, year=y, 
            month_str=months[m-1], 
            month_str_short=months_short[m-1]
        )
        
        y_adm, m_adm, d_adm = random.randint(2020, 2026), random.randint(1, 12), random.randint(1, 28)
        adm_template = random.choice(dates_templates)
        adm_str = adm_template.format(
            day=d_adm, month=m_adm, year=y_adm, 
            month_str=months[m_adm-1], 
            month_str_short=months_short[m_adm-1]
        )
        
        # Hospital name
        if i % 2 == 0:
            hosp = f"{random.choice(hospitals_prefixes)} {random.choice(hospitals_names)}"
        else:
            hosp = f"{random.choice(hospitals_names)} {random.choice(hospitals_suffixes)}"
            
        # Injected abbreviations
        active_abbrevs = random.sample(list(abbrevs.keys()), k=random.randint(3, 6))
        
        # Synthesize raw clinical note text
        raw_text = f"Patient {p_name}, DOB: {dob_str}, Phone: {phone_val}, SSN: {ssn_val}.\n"
        raw_text += f"Admitted to {hosp} on {adm_str} under the supervision of {d_name}.\n\n"
        
        symptoms = []
        therapies = []
        
        if "sob" in active_abbrevs:
            symptoms.append("sob on exertion")
        if "HTN" in active_abbrevs:
            symptoms.append("history of HTN")
        if "DM" in active_abbrevs:
            symptoms.append("DM type II managed with diet")
        if "COPD" in active_abbrevs:
            symptoms.append("chronic COPD exacerbation")
        if "GERD" in active_abbrevs:
            symptoms.append("GERD symptoms")
        if "CKD" in active_abbrevs:
            symptoms.append("underlying CKD stage 3")
        if "CAD" in active_abbrevs:
            symptoms.append("history of CAD and stent placement")
        if "CHF" in active_abbrevs:
            symptoms.append("mild CHF signs")
            
        if not symptoms:
            symptoms.append("no acute symptoms reported")
            
        if "po" in active_abbrevs:
            if "bid" in active_abbrevs:
                therapies.append("Metformin 500mg po bid")
            if "qd" in active_abbrevs:
                therapies.append("Lisinopril 10mg po qd")
            if "prn" in active_abbrevs:
                therapies.append("Paracetamol 1g po prn for pain")
            if "qhs" in active_abbrevs:
                therapies.append("Atorvastatin 20mg po qhs")
        else:
            if "bid" in active_abbrevs:
                therapies.append("Insulin glargine bid")
            if "qd" in active_abbrevs:
                therapies.append("Ramipril 5mg qd")
            if "tid" in active_abbrevs:
                therapies.append("Amoxicillin 500mg tid")
                
        if not therapies:
            therapies.append("no new therapies started")
            
        raw_text += f"Clinical Presentation: {', '.join(symptoms)}.\n"
        raw_text += f"Prescribed Therapy: {', '.join(therapies)}.\n"
        raw_text += f"Italian fiscal identifier associated is {cf_val}. Follow-up in 1 month PRN if condition changes."
        
        # Populate expected abbreviations based on actual presence in the raw note text
        expected_found = []
        for abbrev in abbrevs.keys():
            # Check for word boundary of the abbreviation in the raw text
            if re.search(r'\b' + re.escape(abbrev) + r'\b', raw_text, re.IGNORECASE):
                expected_found.append(abbrev.lower())
                
        # Add long clinical texts (over 2000 chars) for testing the structural boundary-aware chunker
        if i % 5 == 0:
            raw_text = (raw_text + "\n\n") * 5
            
        # Keep track of target sensitive strings to assert they are not leaked
        pii_targets = {
            "NAME": [p_name, d_name, p_first, p_last, d_first, d_last],
            "DATE": [dob_str, adm_str],
            "ID": [ssn_val, cf_val]
        }
        
        # Clean target subsets (only keep strings with realistic values)
        pii_targets["NAME"] = list(set([n for n in pii_targets["NAME"] if len(n) > 2]))
        
        dataset.append({
            "note_id": i + 1,
            "text": raw_text,
            "pii_targets": pii_targets,
            "expected_abbrevs": list(set(expected_found))
        })
        
    return dataset


# --- Failure Analysis & Self-Optimization Engine ---
class AssertionEngine:
    def __init__(self):
        self.failures = []

    def check_pii_leak(self, note_id: int, sanitized_text: str, pii_targets: Dict[str, List[str]]):
        for pii_type, targets in pii_targets.items():
            for target in targets:
                # If target PII value is found verbatim in sanitized text, it's a leak
                if target.lower() in sanitized_text.lower():
                    self.failures.append({
                        "note_id": note_id,
                        "type": "PII_LEAK",
                        "failed_value": target,
                        "pii_type": pii_type,
                        "description": f"Verbatim leak of {pii_type} value '{target}' in sanitized text."
                    })

    def check_normalization(self, note_id: int, normalized_found: List[str], expected_abbrevs: List[str]):
        normalized_found_lower = [t.lower() for t in normalized_found]
        for abbrev in expected_abbrevs:
            if abbrev.lower() not in normalized_found_lower:
                self.failures.append({
                    "note_id": note_id,
                    "type": "NORMALIZATION_FAILURE",
                    "failed_value": abbrev,
                    "description": f"Expected abbreviation '{abbrev}' was not normalized or reported as found."
                })

    def print_suggestions(self):
        if not self.failures:
            print("\n\033[92m[OPTIMIZATION ENGINE] All assertions passed. No structural updates required in main.py!\033[0m")
            return
            
        print("\n" + "="*50)
        print("\033[91m[OPTIMIZATION ENGINE] ASSERTION FAILURES DETECTED - SUGGESTED CORRECTIONS:\033[0m")
        print("="*50)
        
        suggestions = {}
        for fail in self.failures:
            ftype = fail["type"]
            val = fail["failed_value"]
            
            if ftype == "PII_LEAK":
                pii_type = fail["pii_type"]
                if pii_type == "DATE":
                    suggestions[f"DATE_REGEX_{val}"] = (
                        f"Suggestion: Review self.date_re patterns in main.py. "
                        f"Consider adding support for date pattern matching '{val}' using: "
                        r"r'\b\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{2,4}\b' or similar."
                    )
                elif pii_type == "ID":
                    suggestions[f"ID_REGEX_{val}"] = (
                        f"Suggestion: Expand self.ids_re or self.ssn_re to match pattern: '{val}'. "
                        r"Ensure that separators and word boundaries are properly defined."
                    )
                elif pii_type == "NAME":
                    suggestions[f"NAME_REGEX_{val}"] = (
                        f"Suggestion: Enhance self.names_re or prefix-based name regex in main.py to detect: '{val}'."
                    )
            elif ftype == "NORMALIZATION_FAILURE":
                suggestions[f"ABBREV_MAP_{val}"] = (
                    f"Suggestion: Add the abbreviation definition '{val}' to the self.abbrev_map "
                    f"in main.py. Format: r'\\b{val.lower()}\\b': ('<expansion>', '{val.upper()}')"
                )
                
        for idx, (key, sugg) in enumerate(suggestions.items(), 1):
            print(f"{idx}. {sugg}")
        print("="*50 + "\n")


# --- Benchmarking & Concurrency Engine ---
async def send_request(client: httpx.AsyncClient, url: str, note: Dict[str, Any], assertion_engine: AssertionEngine) -> Dict[str, Any]:
    payload = {
        "clinical_note": note["text"],
        "max_tokens": 500
    }
    
    start_time = time.perf_counter()
    try:
        response = await client.post(url, json=payload, timeout=10.0)
        latency = (time.perf_counter() - start_time) * 1000
        
        if response.status_code == 200:
            res_json = response.json()
            sanitized_text = res_json["sanitized_text"]
            normalized_found = res_json["normalized_terms_found"]
            chunks = res_json["chunks"]
            
            # Assertions
            assertion_engine.check_pii_leak(note["note_id"], sanitized_text, note["pii_targets"])
            assertion_engine.check_normalization(note["note_id"], normalized_found, note["expected_abbrevs"])
            
            # Check chunk boundaries
            for chunk in chunks:
                if len(chunk["text"]) > 500:
                    assertion_engine.failures.append({
                        "note_id": note["note_id"],
                        "type": "CHUNKING_LIMIT_EXCEEDED",
                        "failed_value": len(chunk["text"]),
                        "description": f"Chunk {chunk['chunk_id']} exceeds max_tokens length limit ({len(chunk['text'])} > 500 chars)."
                    })
                    
            return {
                "success": True,
                "latency_ms": latency,
                "input_len": len(note["text"]),
                "output_len": len(sanitized_text),
                "chunks_count": len(chunks)
            }
        else:
            return {
                "success": False,
                "error": f"HTTP_{response.status_code}",
                "latency_ms": latency
            }
    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        return {
            "success": False,
            "error": str(e),
            "latency_ms": latency
        }


async def run_benchmark(url: str, concurrency: int = 10):
    print("\n" + "="*50)
    print(f"STARTING MASSIVE STRESS TEST & BENCHMARK")
    print(f"Target URL: {url}")
    print(f"Concurrency level: {concurrency} tasks")
    print("="*50)
    
    dataset = generate_stress_dataset(50)
    assertion_engine = AssertionEngine()
    
    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        # We process requests concurrently in chunks based on concurrency limit
        sem = asyncio.Semaphore(concurrency)
        
        async def worker(note):
            async with sem:
                return await send_request(client, url, note, assertion_engine)
                
        start_time = time.perf_counter()
        tasks = [worker(note) for note in dataset]
        results = await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - start_time
        
    # Analyze metrics
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    total_reqs = len(results)
    success_count = len(successful_results)
    
    latencies = [r["latency_ms"] for r in successful_results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    # Throughput
    throughput = total_reqs / total_duration
    
    # Sanitization Rate (Accuracy)
    pii_leak_count = sum(1 for f in assertion_engine.failures if f["type"] == "PII_LEAK")
    sanitization_rate = ((total_reqs - pii_leak_count) / total_reqs) * 100 if total_reqs else 0
    
    # Chunking efficiency metrics
    total_chunks = sum(r["chunks_count"] for r in successful_results)
    total_output_chars = sum(r["output_len"] for r in successful_results)
    avg_chars_per_chunk = total_output_chars / total_chunks if total_chunks else 0
    
    # Formatting terminal tables
    print("\n" + "-"*50)
    print(f"BENCHMARK SUMMARY REPORT")
    print("-"*50)
    print(f"Total Requests Sent     : {total_reqs}")
    print(f"Successful Requests     : {success_count}")
    print(f"Failed Requests         : {len(failed_results)}")
    print(f"Throughput (RPS)        : {throughput:.2f} req/sec")
    print(f"Total Test Duration     : {total_duration:.3f} seconds")
    print("-"*50)
    print(f"Average Latency         : {avg_latency:.2f} ms")
    print(f"Minimum Latency         : {min_latency:.2f} ms")
    print(f"Maximum Latency         : {max_latency:.2f} ms")
    print("-"*50)
    print(f"Sanitization Rate       : {sanitization_rate:.2f}%")
    print(f"Total Chunks Ingested   : {total_chunks}")
    print(f"Avg Chars per Chunk     : {avg_chars_per_chunk:.1f} (Target limit: 500)")
    print("-"*50)
    
    # Save raw benchmark results to json file
    raw_results = {
        "summary": {
            "total_requests": total_reqs,
            "success_count": success_count,
            "failed_count": len(failed_results),
            "throughput_rps": throughput,
            "total_duration_sec": total_duration,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "sanitization_rate_pct": sanitization_rate,
            "total_chunks": total_chunks,
            "avg_chars_per_chunk": avg_chars_per_chunk
        },
        "failures": assertion_engine.failures
    }
    
    with open("benchmark_results.json", "w") as f:
        json.dump(raw_results, f, indent=2)
        
    print("\n[INFO] Raw benchmark metrics saved to 'benchmark_results.json'")
    
    # Output optimizations and assertions suggestion
    assertion_engine.print_suggestions()


if __name__ == "__main__":
    url_target = "https://clinical-sanitizer-api-731921218341.europe-west1.run.app/api/v1/clinical-sanitize"
    asyncio.run(run_benchmark(url_target, concurrency=10))
