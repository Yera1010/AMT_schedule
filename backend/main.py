from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from services import process_request, delete_lesson_by_id, check_conflict_strict, save_lesson_to_db, get_day_schedule
import shutil
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
import import_csv 

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- МОДЕЛИ ---
class QueryRequest(BaseModel):
    text: str

class ManualLessonRequest(BaseModel):
    teacher: str
    student: str
    subject: str
    room: str       
    day_idx: int
    start_time: str
    duration: int

class DayRequest(BaseModel):
    day_idx: int

# --- ENDPOINTS ---

@app.post("/process-schedule")
async def api_process_schedule(data: QueryRequest):
    return process_request(data.text)

# 👇 ВОТ ЭТОТ МАРШРУТ МЫ ДОБАВИЛИ!
@app.post("/get-daily-schedule")
def api_get_daily_schedule(data: DayRequest):
    db = SessionLocal()
    lessons = get_day_schedule(db, data.day_idx)
    db.close()
    return {"status": "success", "data": lessons}

@app.delete("/delete-lesson/{lesson_id}")
def api_delete_lesson(lesson_id: int):
    db = SessionLocal()
    success = delete_lesson_by_id(db, lesson_id)
    db.close()
    if success: return {"status": "success", "message": "Урок удален"}
    return {"status": "error", "message": "Урок не найден"}

@app.post("/add-lesson-manual")
def api_add_lesson_manual(data: ManualLessonRequest):
    db = SessionLocal()
    try:
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        target_date = monday + timedelta(days=data.day_idx)
        
        start_dt = datetime.strptime(f"{target_date.strftime('%Y-%m-%d')} {data.start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=data.duration)
        
        conflict = check_conflict_strict(db, data.teacher, data.student, data.room, start_dt, end_dt)
        if conflict: return {"status": "conflict", "message": conflict}

        lesson_data = {
            "teacher": data.teacher,
            "student": data.student,
            "subject": data.subject,
            "room": data.room
        }
        save_lesson_to_db(db, lesson_data, start_dt, end_dt)
        
        return {"status": "success", "message": "Урок добавлен!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    if os.path.exists("uploads"): shutil.rmtree("uploads")
    os.makedirs("uploads")
    saved_files = []
    for file in files:
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        saved_files.append(file_path)
    db = SessionLocal()
    try:
        import_csv.import_folder("uploads", db)
        msg = f"✅ Обработано {len(saved_files)} файлов!"
    except Exception as e: msg = f"⚠️ Ошибка: {str(e)}"
    finally: db.close()
    return {"message": msg, "files": [f.filename for f in files]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)