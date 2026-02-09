# backend/app/main.py
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.background import BackgroundTasks
from urllib.parse import urlparse
import io
import logging
import os
import time
import requests 
from fastapi import UploadFile, File
import subprocess
import pandas as pd
import uuid
import shutil
import google.generativeai as genai
import json

# from .xai import SHAPExplainer
from .nmap_scanner import run_nmap_scan, clean_target
from .zap_client import run_zap_scan
from .crawler import SeleniumCrawler
from .report_generator import generate_pdf, generate_pdf_bytes_from_report, build_compact_context, call_gemini_structured
from .utils import compute_risk
from fastapi.middleware.cors import CORSMiddleware
from .chat_router import router as chat_router

from .attack_graph import build_attack_graph, extract_attack_paths
from .killchain_report import generate_killchain_pdf
import base64
import numpy as np   

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
# ================= IDS CONFIG =================

JAVA_PATH = "java"  # or full path if needed
# CIC_JAR_PATH = "./cicflowmeter/SimpleFlowMeterV4-0.0.4-SNAPSHOT.jar"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CIC_JAR_PATH = os.path.join(
    ROOT_DIR,
    "cicflowmeter",
    "SimpleFlowMeterV4-0.0.4-SNAPSHOT.jar"
)

PCAP_WORK_DIR = os.path.join(ROOT_DIR, "cicflowmeter", "runtime")
# temp working directory
PCAP_WORK_DIR = "./cicflowmeter/runtime"

# your deployed IDS model endpoint (RENDER)
IDS_MODEL_URL = "https://ids-dnn.onrender.com/predict"
IDS_EXPLAIN_URL = "https://ids-dnn.onrender.com/explain"

def dataset_cleaner(csv_path: str) -> pd.DataFrame:
    """
    Converts CICFlowMeter 80+ feature CSV
    → reduces to required 52 features for model
    """

    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Column rename mapping (CICFlowMeter → model expected)
    rename_map = {
        "Dst Port": "Destination Port",
        "Total Fwd Packet": "Total Fwd Packets",
        "Total Length of Fwd Packet": "Total Length of Fwd Packets",
        "Fwd Header Length": "Fwd Header Length",
        "Bwd Header Length": "Bwd Header Length",
        "Packet Length Min": "Min Packet Length",
        "Packet Length Max": "Max Packet Length",
        "FWD Init Win Bytes": "Init_Win_bytes_forward",
        "Bwd Init Win Bytes": "Init_Win_bytes_backward",
        "Fwd Act Data Pkts": "act_data_pkt_fwd",
        "Fwd Seg Size Min": "min_seg_size_forward",
        "Label": "Attack Type"
    }

    df = df.rename(columns=rename_map)

    # Required 52 features
    required_columns = [
        "Destination Port","Flow Duration","Total Fwd Packets","Total Length of Fwd Packets",
        "Fwd Packet Length Max","Fwd Packet Length Min","Fwd Packet Length Mean","Fwd Packet Length Std",
        "Bwd Packet Length Max","Bwd Packet Length Min","Bwd Packet Length Mean","Bwd Packet Length Std",
        "Flow Bytes/s","Flow Packets/s","Flow IAT Mean","Flow IAT Std","Flow IAT Max","Flow IAT Min",
        "Fwd IAT Total","Fwd IAT Mean","Fwd IAT Std","Fwd IAT Max","Fwd IAT Min",
        "Bwd IAT Total","Bwd IAT Mean","Bwd IAT Std","Bwd IAT Max","Bwd IAT Min",
        "Fwd Header Length","Bwd Header Length","Fwd Packets/s","Bwd Packets/s",
        "Min Packet Length","Max Packet Length","Packet Length Mean","Packet Length Std",
        "Packet Length Variance","FIN Flag Count","PSH Flag Count","ACK Flag Count",
        "Average Packet Size","Subflow Fwd Bytes",
        "Init_Win_bytes_forward","Init_Win_bytes_backward",
        "act_data_pkt_fwd","min_seg_size_forward",
        "Active Mean","Active Max","Active Min",
        "Idle Mean","Idle Max","Idle Min",
        "Attack Type"
    ]

    # Some CSVs may not contain label → create dummy
    if "Attack Type" not in df.columns:
        df["Attack Type"] = "Unknown"

    # keep only required columns
    df = df[required_columns]

    # fill NaNs
    df = df.replace([np.inf, -np.inf], 0)
    df = df.fillna(0)

    return df

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
    print("Health check OK")
    return {"status": "running", "version": "1.0.0"}

# @app.post("/predict")
# def predict(payload: dict):
#     """
#     payload = {
#         "features": [f1, f2, f3, ...]
#     }
#     """

#     # Convert input
#     X = np.array(payload["features"]).reshape(1, -1)

#     # Scale input
#     X_scaled = scaler.transform(X)

#     # Predict
#     prob = float(model.predict(X_scaled)[0][0])
#     prediction = "Attack" if prob > 0.5 else "Normal"

#     # SHAP explanation
#     shap_values = shap_explainer.explain_instance(X_scaled)
#     explanation = format_shap_explanation(
#         feature_names,
#         shap_values
#     )

#     return {
#         "prediction": prediction,
#         "confidence": round(prob, 4),
#         "explanation": explanation
#     }

@app.post("/ids/pcap")
async def run_ids_pipeline(file: UploadFile = File(...)):
    """
    Upload PCAP → run CICFlowMeter → clean dataset → send to IDS model → return predictions
    """

    logger.info("========== IDS PIPELINE STARTED ==========")

    if not file.filename.endswith(".pcap"):
        logger.error("Uploaded file is not PCAP")
        raise HTTPException(status_code=400, detail="Upload a valid .pcap file")

    job_id = str(uuid.uuid4())
    work_dir = os.path.join(PCAP_WORK_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)

    logger.info(f"[STEP 0] Job ID: {job_id}")
    logger.info(f"[STEP 0] Working directory: {work_dir}")

    try:
        # ---------------------------------------------------
        # 1. SAVE PCAP
        # ---------------------------------------------------
        logger.info("[STEP 1] Saving PCAP file...")

        pcap_path = os.path.join(work_dir, file.filename)

        with open(pcap_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"[STEP 1] PCAP saved successfully: {pcap_path}")

        # ---------------------------------------------------
        # 2. RUN CICFLOWMETER
        # ---------------------------------------------------
        logger.info("[STEP 2] Running CICFlowMeter...")

        abs_work_dir = os.path.abspath(work_dir) + os.sep   # 🔥 IMPORTANT
        abs_jar = os.path.abspath(CIC_JAR_PATH)

        logger.info(f"[FIX] Absolute work dir: {abs_work_dir}")
        logger.info(f"[FIX] Absolute jar path: {abs_jar}")

        cmd = [
            JAVA_PATH,
            "-jar",
            abs_jar,
            abs_work_dir,
            abs_work_dir
        ]

        logger.info(f"[DEBUG] Running command: {' '.join(cmd)}")

        process = subprocess.run(cmd, capture_output=True, text=True)

        logger.info(f"[STEP 2] Return code: {process.returncode}")
        logger.info(f"[STEP 2] STDOUT:\n{process.stdout}")
        logger.info(f"[STEP 2] STDERR:\n{process.stderr}")

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail="CICFlowMeter failed")


        logger.info("[STEP 2] CICFlowMeter completed successfully")

        # ---------------------------------------------------
        # 3. FIND GENERATED CSV
        # ---------------------------------------------------
        logger.info("[STEP 3] Searching for generated CSV...")

        all_files = os.listdir(work_dir)
        logger.info(f"[STEP 3] Files in work_dir: {all_files}")

        csv_files = [f for f in all_files if f.endswith(".csv")]

        if not csv_files:
            logger.error("[STEP 3] No CSV generated by CICFlowMeter")
            raise HTTPException(status_code=500, detail="No CSV generated by CICFlowMeter")

        csv_path = os.path.join(work_dir, csv_files[0])
        logger.info(f"[STEP 3] CSV found: {csv_path}")

        # ---------------------------------------------------
        # 4. CLEAN DATASET
        # ---------------------------------------------------
        logger.info("[STEP 4] Cleaning dataset...")

        cleaned_df = dataset_cleaner(csv_path)

        logger.info(f"[STEP 4] Cleaned dataset rows: {len(cleaned_df)}")
        logger.info(f"[STEP 4] Columns: {list(cleaned_df.columns)}")

        if len(cleaned_df) == 0:
            logger.error("[STEP 4] Cleaned dataset empty")
            raise HTTPException(status_code=500, detail="Dataset empty after cleaning")

        # ---------------------------------------------------
        # 5. SEND TO MODEL
        # ---------------------------------------------------
        logger.info("[STEP 5] Sending data to IDS model...")

        predictions = []
        all_feature_importance = {}

        for idx, row in cleaned_df.iterrows():
            logger.info(f"[STEP 5] Processing row {idx}")
            if idx == 0:
                continue
            try:
                features = row.drop("Attack Type").tolist()
            except Exception as e:
                logger.error(f"[STEP 5] Feature extraction error: {str(e)}")
                continue

            payload = {"features": features}

            # -------- PREDICT --------
            try:
                pred_res = requests.post(IDS_MODEL_URL, json=payload, timeout=60)
                if pred_res.status_code == 200:
                    pred_data = pred_res.json()
                else:
                    pred_data = {"error": pred_res.text}
            except Exception as e:
                pred_data = {"error": str(e)}

            # -------- EXPLAIN --------
            try:
                exp_res = requests.post(IDS_EXPLAIN_URL, json=payload, timeout=60)
                if exp_res.status_code == 200:
                    exp_data = exp_res.json()
                else:
                    exp_data = {}
            except Exception as e:
                logger.error(f"Explain error: {str(e)}")
                exp_data = {}

            # merge prediction + explain
            combined = {
                **pred_data,
                "xai": exp_data.get("chart")
            }

            predictions.append(combined)

            # collect feature importance (for global XAI)
            if exp_data.get("chart") and exp_data["chart"].get("data"):
                for f in exp_data["chart"]["data"]:
                    name = f["feature"]
                    impact = abs(f["impact"])
                    all_feature_importance[name] = all_feature_importance.get(name, 0) + impact

        # -------- GLOBAL XAI SUMMARY --------
        sorted_features = dict(
            sorted(all_feature_importance.items(), key=lambda x: x[1], reverse=True)[:8]
        )

        global_xai = {
            "feature_importance": sorted_features,
            "note": "Top features influencing IDS decisions across flows"
        }
        # ---------------------------------------------------
        # 6. RESPONSE
        # ---------------------------------------------------

        logger.info("[STEP 6] Sending response to frontend")

        return JSONResponse({
            "status": "completed",
            "flows_processed": len(predictions),
            "predictions": predictions[:50],
            "xai": global_xai
        })

    except Exception as e:
        logger.exception("[FATAL ERROR]")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        logger.info("[FINAL] Cleaning temp directory")
        try:
            shutil.rmtree(work_dir)
            logger.info("[FINAL] Temp directory deleted")
        except Exception as e:
            logger.warning(f"[FINAL] Cleanup failed: {str(e)}")

        logger.info("========== IDS PIPELINE END ==========")

def run_gemini_soc_analysis(xai_data: dict):
    """
    SOC analysis using Gemini
    RETURNS always valid dict (never crashes)
    """

    print(GEMINI_KEY)
    if not GEMINI_KEY:
        return {
            "attack_detected": True,
            "attack_type": "Unknown",
            "why_flagged": "Gemini key missing",
            "real_world_impact": "Unknown",
            "mitigation_steps": ["Check Gemini API key"],
            "severity": "Medium",
            "threat_score": 50,
            "confidence": 50
        }

    prompt = f"""
You are a senior SOC analyst.

Analyze IDS XAI output and return ONLY valid JSON.

Format:
{{
 "attack_detected": true/false,
 "attack_type": "string",
 "why_flagged": "string",
 "real_world_impact": "string",
 "mitigation_steps": ["step1","step2"],
 "severity": "Low | Medium | High | Critical",
 "threat_score": number (0-100),
 "confidence": number (0-100)
}}

XAI:
{json.dumps(xai_data, indent=2)}
"""

    try:
        model = genai.GenerativeModel(MODEL)

        response = model.generate_content(
            [{"text": prompt}],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"
            }
        )

        # ---------- SAFE TEXT EXTRACTION ----------
        try:
            text = response.candidates[0].content.parts[0].text
        except:
            return {
                "attack_detected": True,
                "attack_type": "Parsing error",
                "why_flagged": "Gemini response format unexpected",
                "real_world_impact": "Unknown",
                "mitigation_steps": ["Check Gemini response"],
                "severity": "Medium",
                "threat_score": 60,
                "confidence": 60
            }

        if not text:
            raise Exception("Empty Gemini response")

        # ---------- EXTRACT JSON SAFELY ----------
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise Exception("JSON not found in Gemini output")

        json_text = text[start:end+1]

        try:
            parsed = json.loads(json_text)
        except Exception:
            # fallback if malformed
            parsed = {
                "attack_detected": True,
                "attack_type": "Suspicious traffic",
                "why_flagged": "AI detected anomalous network behaviour",
                "real_world_impact": "Potential intrusion or attack",
                "mitigation_steps": ["Investigate traffic", "Block suspicious IP"],
                "severity": "High",
                "threat_score": 75,
                "confidence": 80
            }

        return parsed

    except Exception as e:
        return {
            "attack_detected": True,
            "attack_type": "Analysis failed",
            "why_flagged": str(e),
            "real_world_impact": "Unknown",
            "mitigation_steps": ["Check Gemini API"],
            "severity": "Medium",
            "threat_score": 55,
            "confidence": 50
        }

@app.post("/ids/gemini-soc")
async def gemini_soc_endpoint(payload: dict = Body(...)):
    xai_data = payload.get("xai")

    if not xai_data:
        raise HTTPException(status_code=400, detail="Missing XAI data")

    result = run_gemini_soc_analysis(xai_data)

    # if "error" in result:
    #     raise HTTPException(status_code=500, detail=result["error"])

    return {
        "status": "ok",
        "soc_analysis": result,
        "threat_score": result.get("threat_score", 0),
        "severity": result.get("severity", "Unknown")
    }

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

app.include_router(chat_router, prefix="/api", tags=["Chatbot"])

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
    # ---- SAFE HOST EXTRACTION ----
    hosts = nmap_data.get("hosts", [])
    first_host = hosts[0] if len(hosts) > 0 else {}

    ports_safe = (
        nmap_data.get("ports")
        or first_host.get("ports", [])
        or nmap_data.get("xml_raw", {}).get("nmaprun", {})
    )

    # ---- RESPONSE ----
    response_json = {
        "result": {
            "target": host,
            "scan_mode": mode,
            "risk_score": risk,
            "llm_used": bool(use_llm),
            "ai": ai_output,
            "nmap": {
                "arguments": nmap_data.get("arguments"),
                "ports": ports_safe,
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

@app.post("/security/killchain")
def api_killchain(payload: dict = Body(...)):
    """
    Accepts the existing scan result JSON and builds a kill-chain graph + PDF.
    Frontend can just send the 'results' object it already has.
    """
    try:
        # sometimes payload might already be {"result": {...}}
        result = payload.get("result", payload)
    except AttributeError:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    nmap = result.get("nmap") or {}
    zap = result.get("zap") or {}
    crawler = result.get("crawler") or {}
    ai = result.get("ai") or {}

    # Build graph + attack paths
    G = build_attack_graph(nmap, zap, crawler)
    attack_paths = extract_attack_paths(G)

    # Serialize nodes/edges for ReactFlow
    graph_nodes = []
    type_columns = {"port": 0, "page": 1, "vuln": 2, "threat": 3}
    spacing_y = 90
    counters = {t: 0 for t in type_columns.keys()}

    for node_id, data in G.nodes(data=True):
        t = data.get("type", "other")
        col = type_columns.get(t, 1)
        idx = counters.get(t, 0)
        counters[t] = idx + 1

        x = 200 * col
        y = 60 + spacing_y * idx

        graph_nodes.append({
            "id": node_id,
            "type": t,
            "label": data.get("label", node_id),
            "position": {"x": x, "y": y},
            "data": {
                "label": data.get("label", node_id),
                "risk": data.get("risk"),
                "url": data.get("url"),
            },
        })

    graph_edges = []
    for u, v, data in G.edges(data=True):
        graph_edges.append({
            "id": f"{u}->{v}",
            "source": u,
            "target": v,
            "label": data.get("relation", ""),
        })

    # Build Kill-Chain PDF (XAI + paths)
    pdf_bytes = generate_killchain_pdf(result, attack_paths)
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    return JSONResponse({
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
        "attack_paths": attack_paths,
        "pdf_base64": pdf_b64,
    })

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
