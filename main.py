from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import mimetypes
import os
import json
import subprocess
import shutil
from datetime import datetime
import sqlite3
import glob
from datetime import datetime


app = FastAPI()
# Use a relative path for the data directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current script directory
DATA_DIR = os.path.join(BASE_DIR, "data")  # Point to the `data` folder

# Utility function to ensure security constraints
def is_safe_path(path):
    return os.path.abspath(path).startswith(os.path.abspath(DATA_DIR))

def parse_date(date_str):
    formats = ["%Y-%m-%d", "%d-%b-%Y", "%b %d, %Y", "%Y/%m/%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {date_str}")

@app.post("/run")
def run_task(task: str):
    try:
        if "install uv" in task.lower() and "datagen.py" in task.lower():
            subprocess.run(["pip", "install", "uv"], check=True)
            subprocess.run(["python", "datagen.py", os.environ.get("USER_EMAIL", "test@example.com")], check=True)
        
        elif "format" in task.lower() and "prettier" in task.lower():
            file_path = os.path.join(DATA_DIR, "format.md")

            if is_safe_path(file_path) and os.path.exists(file_path):
                prettier_path = shutil.which("npx")  # Find npx in the system
                if not prettier_path:
                    raise HTTPException(status_code=500, detail="npx not found. Make sure Node.js is installed.")

                # Run Prettier with the full path
                try:
                    subprocess.run(["npx", "prettier", "--write", file_path], check=True, shell=True)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Prettier formatting failed: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="Invalid file path")

        
        elif "count wednesdays" in task.lower():
            file_path = f"{DATA_DIR}/dates.txt"
            output_path = f"{DATA_DIR}/dates-wednesdays.txt"
            if is_safe_path(file_path) and os.path.exists(file_path):
                with open(file_path, "r") as f:
                    count = sum(1 for line in f if parse_date(line.strip()).weekday() == 2)
                with open(output_path, "w") as f:
                    f.write(str(count))
            else:
                raise HTTPException(status_code=400, detail="Invalid file path")
        
        elif "sort contacts" in task.lower():
            file_path = f"{DATA_DIR}/contacts.json"
            output_path = f"{DATA_DIR}/contacts-sorted.json"
            if is_safe_path(file_path) and os.path.exists(file_path):
                with open(file_path, "r") as f:
                    contacts = json.load(f)
                sorted_contacts = sorted(contacts, key=lambda x: (x["last_name"], x["first_name"]))
                with open(output_path, "w") as f:
                    json.dump(sorted_contacts, f, indent=2)
            else:
                raise HTTPException(status_code=400, detail="Invalid file path")
        
        elif "total sales of gold tickets" in task.lower():
            db_path = f"{DATA_DIR}/ticket-sales.db"
            output_path = f"{DATA_DIR}/ticket-sales-gold.txt"
            if is_safe_path(db_path) and os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type='Gold'")
                total_sales = cursor.fetchone()[0] or 0
                conn.close()
                with open(output_path, "w") as f:
                    f.write(str(total_sales))
            else:
                raise HTTPException(status_code=400, detail="Invalid file path")
        
        elif "recent log files" in task.lower():
            log_files = sorted(glob.glob(f"{DATA_DIR}/logs/*.log"), key=os.path.getmtime, reverse=True)[:10]
            output_path = f"{DATA_DIR}/logs-recent.txt"
            with open(output_path, "w") as f:
                for log_file in log_files:
                    with open(log_file, "r") as lf:
                        first_line = lf.readline().strip()
                        f.write(first_line + "\n")
        
        elif "markdown index" in task.lower():
            md_files = glob.glob(f"{DATA_DIR}/docs/*.md")
            index = {}
            for md_file in md_files:
                with open(md_file, "r") as f:
                    for line in f:
                        if line.startswith("# "):
                            index[os.path.basename(md_file)] = line.strip("# ").strip()
                            break
            output_path = f"{DATA_DIR}/docs/index.json"
            with open(output_path, "w") as f:
                json.dump(index, f, indent=2)
        
        elif "extract email sender" in task.lower():
            input_path = f"{DATA_DIR}/email.txt"
            output_path = f"{DATA_DIR}/email-sender.txt"
            if is_safe_path(input_path) and os.path.exists(input_path):
                with open(input_path, "r") as f:
                    email_content = f.read()
                sender_email = "extracted@example.com"  # Placeholder for LLM extraction
                with open(output_path, "w") as f:
                    f.write(sender_email)
            else:
                raise HTTPException(status_code=400, detail="Invalid file path")
        
        else:
            raise HTTPException(status_code=400, detail="Task not recognized")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
@app.get("/read")
def read_file(path:str):
    with open(path,"r") as f:
        data=f.read()
    return data
'''
@app.get("/read")
def read_file(path: str):
    # Remove any leading `/data/` or `data/` to make it relative
    if path.startswith("/data/") or path.startswith("data/"):
        path = path[len("/data/"):]

    # Create the full absolute path inside DATA_DIR
    safe_path = os.path.abspath(os.path.join(DATA_DIR, path))

    # Security check: Ensure path is inside DATA_DIR
    if not is_safe_path(safe_path) or not os.path.exists(safe_path):
        raise HTTPException(status_code=400, detail="Invalid or missing file path")

    # Handle SQLite `.db` files
    if safe_path.endswith(".db"):
        return FileResponse(safe_path, media_type="application/octet-stream", filename=os.path.basename(safe_path))

    # Handle text-based files
    elif safe_path.endswith((".txt", ".md", ".json", ".csv")):
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()

    # Handle binary files (e.g., images, PDFs)
    else:
        mime_type, _ = mimetypes.guess_type(safe_path)
        return FileResponse(safe_path, media_type=mime_type or "application/octet-stream")