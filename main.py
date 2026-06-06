from contextlib import asynccontextmanager
from typing import Optional
import io, os, time

import pandas as pd
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import init_db, get_connection, verify_user
from analytics import search_patient, analyse_medicine, generate_doctor_chart, get_summary_kpis

REQUIRED_COLUMNS = {
    "Patient_ID", "Name", "Age", "Gender", "Disease",
    "Medicine", "Dosage", "Reaction", "Recovery", "Visit_Date", "Doctor",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="ArogyaInsight Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_user(username.strip(), password.strip()):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html",
        context={"error": "Incorrect username or password...try again"},
    )

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, success: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="upload.html", context={"success": success})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    kpis      = get_summary_kpis()
    doc_table = generate_doctor_chart()
    doctors   = doc_table[["Rank", "Doctor", "Total_Patients", "Fully_Recovered", "Recovery_Rate"]].to_dict(orient="records")
    ts = int(time.time())
    return templates.TemplateResponse(request=request, name="dashboard.html",
        context={"kpis": kpis, "doctors": doctors, "ts": ts})

@app.post("/add-patient")
async def add_patient(request: Request,
    Patient_ID: str = Form(...), Name: str = Form(...), Age: int = Form(...),
    Gender: str = Form(...), Disease: str = Form(...), Medicine: str = Form(...),
    Dosage: str = Form(...), Reaction: str = Form(...), Recovery: str = Form(...),
    Visit_Date: str = Form(...), Doctor: str = Form(...)):
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO patient_records
                    (Patient_ID, Name, Age, Gender, Disease, Medicine, Dosage, Reaction, Recovery, Visit_Date, Doctor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (Patient_ID, Name, Age, Gender, Disease, Medicine, Dosage, Reaction, Recovery, Visit_Date, Doctor))
            conn.commit()
    except Exception as e:
        return templates.TemplateResponse(request=request, name="upload.html", context={"error": f"Insert failed: {e}"})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/upload-csv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        return templates.TemplateResponse(request=request, name="upload.html", context={"error": "upload only .csv file"})
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        return templates.TemplateResponse(request=request, name="upload.html", context={"error": f"CSV is not parsed: {e}"})
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return templates.TemplateResponse(request=request, name="upload.html",
            context={"error": f"these columns are missing : {', '.join(missing)}"})
    df = df[list(REQUIRED_COLUMNS)]
    try:
        with get_connection() as conn:
            df.to_sql("patient_records", conn, if_exists="append", index=False)
    except Exception as e:
        return templates.TemplateResponse(request=request, name="upload.html", context={"error": f"Database error: {e}"})
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/api/search-patient")
async def api_search_patient(q: str = ""):
    if not q.strip():
        return JSONResponse({"records": [], "message": "type something"})
    results = search_patient(q)
    return JSONResponse({"records": results, "count": len(results)})

@app.get("/api/medicine-stats")
async def api_medicine_stats(medicine: str = ""):
    if not medicine.strip():
        return JSONResponse({"found": False, "message": "Write down Medicine name"})
    stats = analyse_medicine(medicine)
    if not stats.get("found"):
        return JSONResponse({"found": False, "message": f"'{medicine}'no record found"})
    return JSONResponse(stats)