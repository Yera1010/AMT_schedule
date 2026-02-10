import os
import datetime
import json
import re
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import SessionLocal, Lesson

# --- 1. СПИСКИ ---

TEACHERS_LIST = [
    "Adina", "Assel", "Bagdan", "Damir", "Diana", 
    "Erkezhan", "Polina", "Raushan", 
    "Shapagat", "Togzhan", "Yernur"
]

STUDENTS_LIST = [
    "Ayazhan", "Diana", 
    "Turan", "Zhasmin", 
    "Zere", "Kaisar", "Alua",
    "Madina", "Karima","Sultanali"
]

NAME_MAP = {
    "адин": "Adina", "адина": "Adina", "адины": "Adina",
    "асель": "Assel", "багдан": "Bagdan", "дамир": "Damir",
    "диана": "Diana", "дианы": "Diana", "еркежан": "Erkezhan",
    "мадияр": "Madiyar", "полина": "Polina", "полины": "Polina",
    "раушан": "Raushan", "шапагат": "Shapagat", "тогжан": "Togzhan",
    "ернур": "Yernur", "кайсар": "Kaisar", "кайсара": "Kaisar",
    "мадина": "Madina", "мадины": "Madina", "аяжан": "Ayazhan",
    "жасмин": "Zhasmin", "зере": "Zere", "алуа": "Alua",
    "карима": "Karima", "султанали": "Sultanali"
}

# --- 2. КОНФИГУРАЦИЯ AI ---
raw_key = "AIzaSyDjHC2-LYATSqmSr8DKXEjUJqZ80hK56Gk" 
GEMINI_API_KEY = raw_key.strip()
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
MODEL_NAME = 'gemini-exp-1206' 
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- 3. КАЛЕНДАРЬ ---
def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        try: creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except: creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request())
            except: creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token: token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

# --- 4. ФУНКЦИИ БАЗЫ ДАННЫХ ---

def get_weekly_slots(db: Session, name: str, role: str = None):
    query = db.query(Lesson)
    if role == "Teacher":
        query = query.filter(Lesson.teacher_name.ilike(f"%{name}%"))
    elif role == "Student":
        query = query.filter(Lesson.student_name.ilike(f"%{name}%"))
    else:
        query = query.filter(or_(Lesson.teacher_name.ilike(f"%{name}%"), Lesson.student_name.ilike(f"%{name}%")))

    all_lessons = query.all()
    unique_slots = {}
    
    for l in all_lessons:
        day_idx = l.start_time.weekday()
        time_str = l.start_time.strftime("%H:%M")
        key = (day_idx, time_str)
        
        if key not in unique_slots:
            unique_slots[key] = {
                "id": l.id,
                "day_idx": day_idx,
                "start": time_str,
                "end": l.end_time.strftime("%H:%M"),
                "subject": l.subject,
                "teacher": l.teacher_name,
                "student": l.student_name,
                "room": l.room or "Cab 1"
            }
    return list(unique_slots.values())

def get_day_schedule(db: Session, day_idx: int):
    """Возвращает ВСЕ уроки за конкретный день недели для режима 'По кабинетам'"""
    all_lessons = db.query(Lesson).all()
    day_lessons = []
    
    for l in all_lessons:
        if l.start_time.weekday() == day_idx:
            day_lessons.append({
                "id": l.id,
                "start": l.start_time.strftime("%H:%M"),
                "end": l.end_time.strftime("%H:%M"),
                "subject": l.subject,
                "teacher": l.teacher_name,
                "student": l.student_name,
                "room": l.room or "Cab 1"
            })
            
    return day_lessons

def delete_lesson_by_id(db: Session, lesson_id: int):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        db.delete(lesson)
        db.commit()
        return True
    return False

def check_conflict_strict(db: Session, teacher_name: str, student_name: str, room: str, start_dt: datetime, end_dt: datetime):
    # 1. Учитель
    teacher_conflict = db.query(Lesson).filter(
        Lesson.teacher_name.ilike(f"%{teacher_name}%"),
        Lesson.start_time < end_dt, Lesson.end_time > start_dt
    ).first()
    if teacher_conflict: return f"⛔ {teacher_name} занят(а)!"

    # 2. Ученик
    if student_name and student_name.lower() != "unknown":
        student_conflict = db.query(Lesson).filter(
            Lesson.student_name.ilike(f"%{student_name}%"),
            Lesson.start_time < end_dt, Lesson.end_time > start_dt
        ).first()
        if student_conflict: return f"⛔ {student_name} занят(а)!"

    # 3. Кабинет
    if room:
        room_conflict = db.query(Lesson).filter(
            Lesson.room == room,
            Lesson.start_time < end_dt, Lesson.end_time > start_dt
        ).first()
        if room_conflict: return f"⛔ Кабинет {room} занят! ({room_conflict.teacher_name})"
    
    return None

def save_lesson_to_db(db: Session, data: dict, start_dt, end_dt):
    new_lesson = Lesson(
        teacher_name=data.get('teacher', 'Unknown'),
        student_name=data.get('student', 'Unknown'),
        subject=data.get('subject', 'Lesson'),
        room=data.get('room', 'Cab 1'), # Сохраняем кабинет
        start_time=start_dt,
        end_time=end_dt,
        source_file="Manual"
    )
    db.add(new_lesson)
    db.commit()

# --- 5. ЛОГИКА ПОИСКА ---

def analyze_intent_locally(text: str):
    text_lower = text.lower()
    booking_keywords = ['add', 'book', 'set', 'new', 'добавь', 'запиши', 'поставь', 'назначь']
    if any(k in text_lower for k in booking_keywords) and len(text.split()) > 2:
        return None 

    for t in TEACHERS_LIST:
        if t.lower() in text_lower: return {"intent": "QUERY", "person": t, "role": "Teacher"}
    for s in STUDENTS_LIST:
        if s.lower() in text_lower: return {"intent": "QUERY", "person": s, "role": "Student"}
    for rus, eng in NAME_MAP.items():
        if rus in text_lower:
            role = "Teacher" if eng in TEACHERS_LIST else "Student"
            return {"intent": "QUERY", "person": eng, "role": role}
    return None

def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return None

def ai_analyze_intent(user_text: str):
    print(f"🔄 AI запрос: {user_text}")
    model = genai.GenerativeModel(MODEL_NAME)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    teachers_str = ", ".join(TEACHERS_LIST)
    students_str = ", ".join(STUDENTS_LIST)

    prompt = f"""
    Current Date: {today}. User Input: "{user_text}"
    CONTEXT: Teachers: {teachers_str}. Students: {students_str}.
    RETURN JSON ONLY:
    If QUERY: {{ "intent": "QUERY", "person": "Name", "role": "Teacher/Student/Ambiguous" }}
    If BOOK: {{ "intent": "BOOK", "teacher": "Name", "student": "Name", "subject": "Subject", "start": "YYYY-MM-DDTHH:MM:SS", "duration": 60 }}
    """
    try:
        response = model.generate_content(prompt)
        return extract_json(response.text)
    except Exception as e:
        print(f"⚠️ Ошибка AI: {e}")
        return None

# --- 6. ORCHESTRATOR ---

def process_request(user_text: str):
    db = SessionLocal()
    data = analyze_intent_locally(user_text)
    if not data: data = ai_analyze_intent(user_text)

    if not data: 
        db.close()
        return {"status": "error", "message": "Не понял запрос."}

    intent = data.get("intent")
    
    if intent == "QUERY":
        person = data.get("person")
        role = data.get("role")
        weekly_data = get_weekly_slots(db, person, role)
        db.close()
        return {
            "status": "success", 
            "message": f"Расписание: {person}", 
            "type": "weekly_table", 
            "data": weekly_data, 
            "person": person
        }

    elif intent == "BOOK":
        try: start_dt = datetime.datetime.fromisoformat(data['start'])
        except: start_dt = datetime.datetime.now()
        
        end_dt = start_dt + datetime.timedelta(minutes=data.get('duration', 60))
        teacher = data.get('teacher')
        student = data.get('student')

        if teacher and teacher != "TBD":
            conflict_msg = check_conflict_strict(db, teacher, student, None, start_dt, end_dt)
            if conflict_msg:
                db.close()
                return {"status": "conflict", "message": conflict_msg}

        save_lesson_to_db(db, data, start_dt, end_dt)
        db.close()
        return {"status": "success", "type": "booking", "message": f"✅ Урок добавлен: {teacher}"}
            
    db.close()
    return {"status": "error", "message": "Неизвестная команда"}