import os
import pandas as pd
import re
from datetime import datetime, timedelta
from database import SessionLocal, Lesson

# Словарь дней недели (учитываем возможные пробелы "Monday ")
DAYS_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
}

def parse_cell(cell_value):
    """Разбирает ячейку: 'Teacher\nSubject\n14.00 - 16.00'"""
    if not isinstance(cell_value, str) or not cell_value.strip():
        return None
    
    parts = [p.strip() for p in cell_value.split('\n') if p.strip()]
    if len(parts) < 3:
        return None

    teacher = parts[0]
    subject = parts[1]
    time_range = parts[-1] 

    # Чистим время от лишних символов
    times = re.split(r'\s*-\s*', time_range)
    if len(times) != 2:
        return None
    
    # Заменяем точки на двоеточия (14.00 -> 14:00)
    start_str = times[0].replace('.', ':').strip()
    end_str = times[1].replace('.', ':').strip()

    return {
        "teacher": teacher,
        "subject": subject,
        "start_str": start_str,
        "end_str": end_str
    }

def import_folder(folder_path, db):
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"📂 Найдено CSV файлов: {len(files)}")
    
    count_success = 0

    for filename in files:
        # Достаем имя ученика: "Students schedule new - Turan.csv" -> "Turan"
        student_name = "Unknown"
        if " - " in filename:
            student_name = filename.split(" - ")[1].replace(".csv", "").strip()
        else:
            student_name = filename.replace(".csv", "")
        
        file_path = os.path.join(folder_path, filename)
        print(f"🔄 Читаю файл: {filename} (Студент: {student_name})")

        try:
            # 1. Сначала читаем просто как текст, чтобы найти, где начинается таблица
            # (Excel часто добавляет пустые строки сверху)
            header_row_idx = None
            
            # Пробуем разные кодировки, так как Excel может чудить
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']
            df_raw = None
            
            for enc in encodings:
                try:
                    df_raw = pd.read_csv(file_path, header=None, encoding=enc)
                    break
                except:
                    continue
            
            if df_raw is None:
                print(f"❌ Не удалось прочитать {filename} ни в одной кодировке.")
                continue

            # Ищем строку, где есть "Monday" или "Time"
            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.lower().tolist()
                # Если в строке есть слово "monday", значит это заголовок
                if any("monday" in s for s in row_str):
                    header_row_idx = i
                    print(f"   📍 Заголовок найден на строке {i}")
                    break
            
            if header_row_idx is None:
                print(f"⚠️ Не нашел заголовок таблицы в {filename}")
                continue

            # 2. Читаем уже нормально, зная заголовок
            df = pd.read_csv(file_path, header=header_row_idx)
            
            # Дата начала недели (текущий понедельник)
            today = datetime.now()
            monday_date = today - timedelta(days=today.weekday())
            monday_date = monday_date.replace(hour=0, minute=0, second=0, microsecond=0)

            lessons_added = 0

            # Проходим по колонкам
            for col_name in df.columns:
                # Очищаем название колонки: "Monday " -> "monday"
                day_clean = str(col_name).strip().lower().split(' ')[0]
                
                if day_clean not in DAYS_MAP:
                    continue
                
                day_idx = DAYS_MAP[day_clean]
                current_day_date = monday_date + timedelta(days=day_idx)

                # Проходим по ячейкам
                for _, row in df.iterrows():
                    cell_data = parse_cell(row[col_name])
                    
                    if cell_data:
                        try:
                            # Собираем дату и время
                            start_dt = datetime.strptime(f"{current_day_date.strftime('%Y-%m-%d')} {cell_data['start_str']}", "%Y-%m-%d %H:%M")
                            end_dt = datetime.strptime(f"{current_day_date.strftime('%Y-%m-%d')} {cell_data['end_str']}", "%Y-%m-%d %H:%M")
                            
                            # Сохраняем в БД
                            new_lesson = Lesson(
                                teacher_name=cell_data['teacher'],
                                student_name=student_name,
                                subject=cell_data['subject'],
                                room="Cab 1", # По умолчанию
                                start_time=start_dt,
                                end_time=end_dt,
                                source_file=filename
                            )
                            db.add(new_lesson)
                            lessons_added += 1
                        except ValueError:
                            pass # Пропускаем битое время

            db.commit()
            print(f"✅ {student_name}: добавлено {lessons_added} уроков.")
            count_success += 1

        except Exception as e:
            print(f"❌ Критическая ошибка с файлом {filename}: {e}")
            db.rollback()

    print(f"🏁 Итог: Обработано {count_success} из {len(files)} файлов.")