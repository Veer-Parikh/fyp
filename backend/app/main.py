# backend/app/main.py
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.background import BackgroundTasks
from urllib.parse import urlparse
import io
import logging
import os
import time
import requests # NOTE: You must install this package: pip install requests
import json
from .nmap_scanner import run_nmap_scan, clean_target
from .zap_client import run_zap_scan
from .crawler import SeleniumCrawler
from .report_generator import generate_pdf, generate_pdf_bytes_from_report, build_compact_context, call_gemini_structured
from .utils import compute_risk
from fastapi.middleware.cors import CORSMiddleware



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scan-api")

app = FastAPI(title="FAST Scan API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _hostname(target: str) -> str:
    parsed = urlparse(target)
    return parsed.hostname or target


@app.get("/")
def root():
    return {"status": "running", "version": "1.0.0"}


# NMAP Endpoint
@app.get("/scan/nmap")
def api_nmap(target: str, mode: str = Query("fast", regex="^(fast|normal|deep)$"), pdf: bool = False):
    host = clean_target(target)
    result = run_nmap_scan(host, mode=mode)
    risk = compute_risk(result, {"summary": {"counts": {}}})
    payload = {"target": target, "host": host, "risk_score": risk, "nmap": result}
    if pdf:
        pdf_bytes = generate_pdf_bytes_from_report(target, result, {"alerts": [], "summary": {}}, {"pages": [], "xhr": []}, risk, use_llm=False)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=scan-nmap.pdf"})
    return JSONResponse(payload)


# ZAP Endpoint
@app.get("/scan/zap")
def api_zap(target: str, mode: str = Query("fast", regex="^(fast|normal|deep)$"), pdf: bool = False):
    # mode currently influences spider_only or deeper active scan in future
    spider_only = (mode == "fast")
    zap = run_zap_scan(target, spider_only=spider_only)
    risk = compute_risk({"hosts": []}, zap)
    payload = {"target": target, "risk_score": risk, "zap": zap}
    if pdf:
        pdf_bytes = generate_pdf_bytes_from_report(target, {"hosts": []}, zap, {"pages": [], "xhr": []}, risk, use_llm=False)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=scan-zap.pdf"})
    return JSONResponse(payload)


# Crawler Endpoint
@app.get("/scan/crawl")
def api_crawl(target: str, max_pages: int = 100, depth: int = 2, headless: bool = True, pdf: bool = False):
    crawler = SeleniumCrawler(max_pages=max_pages, headless=headless)
    try:
        crawl_data = crawler.crawl(target, max_depth=depth)
    finally:
        crawler.close()
    payload = {"target": target, "crawl": crawl_data}
    if pdf:
        # produce pdf with empty nmap/zap placeholders
        pdf_bytes = generate_pdf_bytes_from_report(target, {"hosts": []}, {"alerts": [], "summary": {}}, crawl_data, 0.0, use_llm=False)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=scan-crawl.pdf"})
    return JSONResponse(payload)


# Combined endpoint: Nmap + ZAP (+ optional crawler)

# @app.get("/scan/combined")
# def api_combined(
#     target: str,
#     mode: str = Query("fast", regex="^(fast|deep|extreme)$"),
#     crawl: bool = False,
#     crawl_pages: int = 50,
#     crawl_depth: int = 2,
#     use_llm: bool = True,
#     pdf: bool = False,
#     model: Optional[str] = None
# ):
#     print("Starting combined scan for", target)
#     host = clean_target(target)
#     print("Cleaned host:", host)

#     # ---------------------------------------------------------
#     # 1. NMAP SCAN (fast / deep / extreme)
#     # ---------------------------------------------------------
#     print(f"Running Nmap scan (mode={mode})...")
#     nmap_data = run_nmap_scan(host, mode=mode)
#     print("Nmap scan completed.")

#     # ---------------------------------------------------------
#     # 2. OPTIONAL CRAWLER (RUN BEFORE ZAP)
#     # ---------------------------------------------------------
#     crawl_data = {"pages": [], "xhr": []}
#     crawler_urls = []

#     if crawl:
#         print("Running crawler...")
#         crawler = SeleniumCrawler(max_pages=crawl_pages, headless=True)
#         try:
#             crawl_data = crawler.crawl(target, max_depth=crawl_depth)
#             crawler_urls = [p["url"] for p in crawl_data.get("pages", [])]
#         finally:
#             crawler.close()
#         print("Crawler completed.")

#     # ---------------------------------------------------------
#     # 3. ZAP SCAN (fast → spider only, deep → passive, extreme → active)
#     # ---------------------------------------------------------
#     print(f"Running ZAP (mode={mode})...")
#     zap_data = run_zap_scan(
#         target,
#         mode=mode,
#         crawler_urls=crawler_urls
#     )
#     print("ZAP scan completed.")

#     # ---------------------------------------------------------
#     # 4. RISK SCORE + RESPONSE
#     # ---------------------------------------------------------
#     risk = compute_risk(nmap_data, zap_data)

#     response_json = {
#         "target": target,
#         "host": host,
#         "mode": mode,
#         "risk_score": risk,
#         "nmap": nmap_data,
#         "zap": zap_data,
#         "crawl": crawl_data,
#     }

#     # ---------------------------------------------------------
#     # 5. PDF OUTPUT (OPTIONAL)
#     # ---------------------------------------------------------
#     if pdf:
#         pdf_bytes = generate_pdf_bytes_from_report(
#             target, nmap_data, zap_data, crawl_data, risk,
#             use_llm=use_llm,
#             model=model
#         )
#         return StreamingResponse(
#             io.BytesIO(pdf_bytes),
#             media_type="application/pdf",
#             headers={"Content-Disposition": f"attachment; filename=scan-combined-{host}.pdf"}
#         )

#     return JSONResponse(response_json)
# paste this into backend/app/main.py (replace the old api_combined)

@app.get("/scan/combined")
def api_combined(
    target: str,
    mode: str = Query("fast", regex="^(fast|deep|extreme)$"),
    crawl: bool = False,
    crawl_pages: int = 50,
    crawl_depth: int = 2,
    use_llm: bool = True,
    pdf: bool = False,
    model: Optional[str] = None
):
    print("Starting combined scan for", target)
    host = clean_target(target)
    print("Cleaned host:", host)

    # 1) NMAP
    print(f"Running Nmap scan (mode={mode})...")
    nmap_data = run_nmap_scan(host, mode=mode)
    print("Nmap scan completed.")

    # 2) CRAWLER (run before ZAP so ZAP can use discovered URLs)
    crawl_data = {"pages": [], "xhr": [], "js_files": []}
    crawler_urls = []
    if crawl:
        print("Running crawler...")
        crawler = SeleniumCrawler(max_pages=crawl_pages, headless=True)
        try:
            crawl_data = crawler.crawl(target, max_depth=crawl_depth)
            crawler_urls = [p.get("url") for p in crawl_data.get("pages", []) if p.get("url")]
        finally:
            crawler.close()
        print("Crawler completed.")

    # 3) ZAP
    print(f"Running ZAP (mode={mode})...")
    zap_data = run_zap_scan(target, mode=mode, crawler_urls=crawler_urls)
    print("ZAP scan completed.")

    # 4) Risk
    risk = compute_risk(nmap_data, zap_data)

   # 5) LLM — run ONCE and reuse for both JSON response and PDF
    ai_output = None
    if use_llm:
        try:
            compact = build_compact_context(nmap_data, zap_data, crawl_data, risk)
            prompt = (
                f"You are reviewing the following scan summary for {target}.\n\n"
                f"{compact}\n\n"
                "Return ONLY valid JSON with keys: executive_summary, technical_analysis, conclusion, remediation."
            )
            ai_output = call_gemini_structured(prompt, model=model)
            print("LLM OUTPUT:", ai_output)
        except Exception as e:
            ai_output = {"error": "exception", "message": str(e)}
            print("LLM ERROR:", e)

    # 6) Build structured JSON result (include ai_output)
    response_json = {
        "result": {
            "target": host,
            "scan_mode": mode,
            "risk_score": risk,
            "llm_used": bool(use_llm),
            "ai": ai_output,
            "nmap": {
                "arguments": nmap_data.get("arguments"),
                "ports": (
                    nmap_data.get("ports")
                    or nmap_data.get("hosts", [{}])[0].get("ports", [])
                    or nmap_data.get("xml_raw", {}).get("nmaprun", {})
                ),
                "raw": nmap_data.get("xml_raw", nmap_data.get("raw"))
            },
            "zap": {
                "mode": zap_data.get("mode"),
                "alerts": zap_data.get("alerts", []),
                "passive": zap_data.get("passive", [])
            },
            "crawler": {
                "pages": crawl_data.get("pages", []),
                "xhr_calls": crawl_data.get("xhr", []),
                "js_files": crawl_data.get("js_files", []),
            }
        }
    }

    # 7) Optional PDF - pass the same ai_output to generate_pdf (no extra kwargs)
    if pdf:
        try:
            pdf_bytes = generate_pdf(
                target,
                nmap_data,
                zap_data,
                crawl_data,
                risk,
                ai=ai_output
            )

            # Base64 encode PDF and return inside JSON body
            import base64
            pdf_b64 = base64.b64encode(pdf_bytes).decode()

            return JSONResponse({
                "pdf_base64": pdf_b64,
                "result": response_json["result"]
            })

        except Exception as e:
            return JSONResponse({"error": f"PDF generation failed: {str(e)}"}, status_code=500)


    return JSONResponse(response_json)


# @app.get("/scan/combined")
# def api_combined(
#     target: str,
#     mode: str = Query("fast", regex="^(fast|normal|deep)$"),
#     crawl: bool = False,
#     crawl_pages: int = 50,
#     crawl_depth: int = 2,
#     use_llm: bool = True,
#     pdf: bool = False,
#     model: Optional[str] = None
# ):
#     print("Starting combined scan for", target)
#     host = clean_target(target)
#     print("Cleaned host:", host)

#     # ⛔ Skip Nmap for testing
#     print("Skipping Nmap...")
#     nmap_data = {
#         "status": "skipped",
#         "hosts": []
#     }

#     # Run ZAP
#     print("Running ZAP scan...")
#     zap_data = run_zap_scan(target, spider_only=(mode == "fast"))
#     print("ZAP scan completed.")

#     # Optional crawler
#     crawl_data = {"pages": [], "xhr": []}
#     print("Crawler starting..." if crawl else "Crawler skipped.")
#     if crawl:
#         crawler = SeleniumCrawler(max_pages=crawl_pages, headless=True)
#         try:
#             crawl_data = crawler.crawl(target, max_depth=crawl_depth)
#         finally:
#             crawler.close()
#     print("Crawler done.")

#     # SAFE RISK SCORE
#     risk = compute_risk(nmap_data, zap_data)

#     response_json = {
#         "target": target,
#         "host": host,
#         "risk_score": risk,
#         "nmap": nmap_data,
#         "zap": zap_data,
#         "crawl": crawl_data
#     }

#     # PDF option
#     if pdf:
#         pdf_bytes = generate_pdf_bytes_from_report(
#             target, nmap_data, zap_data, crawl_data,
#             risk, use_llm=use_llm, model=model
#         )
#         return StreamingResponse(
#             io.BytesIO(pdf_bytes),
#             media_type="application/pdf",
#             headers={"Content-Disposition": f"attachment; filename=scan-combined-{host}.pdf"}
#         )

#     return JSONResponse(response_json)

# from fastapi import FastAPI
# from fastapi.responses import StreamingResponse
# from urllib.parse import urlparse
# from .nmap_scanner import run_nmap_scan
# from .zap_client import run_zap_scan
# from .utils import compute_risk
# from .report_generator import generate_pdf
# import io
# import google.generativeai as genai
# import os

# app = FastAPI()

# def _hostname(target: str):
#     parsed = urlparse(target)
#     return parsed.hostname or target

# @app.get("/")
# def root():
#     return {"status": "running fast mode"}

# @app.get("/scan/fast")
# def fast_scan(target: str):
#     host = _hostname(target)

#     nmap_data = run_nmap_scan(host, mode="fast")
#     zap_data = run_zap_scan(target, spider_only=True)
#     risk = compute_risk(nmap_data, zap_data)

#     return {
#         "target": target,
#         "host": host,
#         "risk_score": risk,
#         "nmap": nmap_data,
#         "zap": zap_data
#     }

# @app.get("/scan/pdf_fast")
# def fast_pdf(target: str):
#     host = _hostname(target)

#     nmap_data = run_nmap_scan(host, mode="fast")
#     zap_data = run_zap_scan(target, spider_only=True)
#     risk = compute_risk(nmap_data, zap_data)

#     pdf_bytes = generate_pdf(
#         target=target,
#         nmap_data=nmap_data,
#         zap_data=zap_data,
#         crawl_data={"pages": [], "xhr": []},  # NO SLOW CRAWLER
#         risk_score=risk,
#         use_llm=True   # disable AI for speed
#     )

#     return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
#                              headers={"Content-Disposition": "attachment; filename=scan-report-fast.pdf"})


@app.get("/test/ai_key")
def test_ai_key():
    """
    Tests if the GEMINI_API_KEY environment variable is set and working by 
    making a simple request to the Gemini API.
    """
    # Use os.environ.get() to safely retrieve the key
    api_key = os.environ.get("GEMINI_API_KEY") 

    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY environment variable not found."}

    # Define the minimal test API call parameters
    test_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": "Test API key connectivity"}]}]
    }

    try:
        # Send the request to the Gemini API
        response = requests.post(
            f"{test_url}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=30 # Set a timeout for the request
        )
        
        # Check for successful authentication (200 OK)
        if response.status_code == 200:
            return {"status": "success", "message": "API Key is valid and authentication successful.", "model_response_status": 200}
        
        # Handle common API key errors (e.g., 400 Bad Request, 403 Forbidden)
        elif response.status_code in (400, 403, 401):
            return {
                "status": "error", 
                "message": f"API Key failed authentication or request error (Status: {response.status_code}). Check if the key is correct or if the service is enabled.", 
                "model_response_status": response.status_code,
                "api_response_snippet": response.text[:150] # Return snippet for debugging
            }
        
        # Handle other unexpected HTTP issues
        else:
            return {
                "status": "warning", 
                "message": f"API call returned unexpected status code {response.status_code}. Key might be valid, but the service might be experiencing issues.",
                "model_response_status": response.status_code,
                "api_response_snippet": response.text[:150]
            }

    except requests.exceptions.RequestException as e:
        # Handle network connectivity errors
        return {"status": "error", "message": f"Network or connection error during API call: {e}"}