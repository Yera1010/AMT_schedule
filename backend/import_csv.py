import os
import pandas as pd
import re
from datetime import datetime, timedelta
from database import SessionLocal, Lesson

# Словарь дней недели
DAYS_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
}

def parse_cell(cell_value):
    """
    Разбирает ячейку формата:
    "Togzhan
     Summer Essay
     14.00 - 16.00"
    """
    if not isinstance(cell_value, str):
        return None
    
    parts = [p.strip() for p in cell_value.split('\n') if p.strip()]
    
    if len(parts) < 3:
        return None

    teacher = parts[0]
    subject = parts[1]
    time_range = parts[-1] # Обычно время в конце "14.00 - 16.00"

    # Парсим время "14.00 - 16.00" или "14:00 - 16:00"
    times = re.split(r'\s*-\s*', time_range)
    if len(times) != 2:
        return None
    
    start_str = times[0].replace('.', ':')
    end_str = times[1].replace('.', ':')

    return {
        "teacher": teacher,
        "subject": subject,
        "start_str": start_str,
        "end_str": end_str
    }

def import_folder(folder_path, db):
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"📂 Найдено файлов: {len(files)}")

    for filename in files:
        # 1. Достаем имя ученика из названия файла
        # Пример: "Students schedule new - Turan.csv" -> "Turan"
        student_name = "Unknown"
        if " - " in filename:
            student_name = filename.split(" - ")[1].replace(".csv", "").strip()
        
        file_path = os.path.join(folder_path, filename)
        print(f"🔄 Обработка: {student_name} ({filename})")

        try:
            # Читаем CSV. Ищем строку, где есть "Time:" или "Monday"
            df = pd.read_csv(file_path, header=None)
            
            # Находим строку заголовка
            header_row_idx = None
            for i, row in df.iterrows():
                row_str = row.astype(str).str.lower().tolist()
                if any("monday" in s for s in row_str):
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                print(f"⚠️ Не нашел заголовок в {filename}")
                continue

            # Перезагружаем с правильным заголовком
            df = pd.read_csv(file_path, header=header_row_idx)
            
            # Определяем дату начала недели (берем текущий понедельник)
            today = datetime.now()
            monday_date = today - timedelta(days=today.weekday())
            monday_date = monday_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Проходим по колонкам (Дни недели)
            for col_name in df.columns:
                day_clean = col_name.strip().split(' ')[0] # "Monday " -> "Monday"
                if day_clean not in DAYS_MAP:
                    continue
                
                day_idx = DAYS_MAP[day_clean]
                current_day_date = monday_date + timedelta(days=day_idx)

                # Проходим по строкам (Ячейки)
                for _, row in df.iterrows():
                    cell_data = parse_cell(row[col_name])
                    
                    if cell_data:
                        # Создаем объекты времени
                        try:
                            start_time = datetime.strptime(f"{current_day_date.strftime('%Y-%m-%d')} {cell_data['start_str']}", "%Y-%m-%d %H:%M")
                            end_time = datetime.strptime(f"{current_day_date.strftime('%Y-%m-%d')} {cell_data['end_str']}", "%Y-%m-%d %H:%M")
                            
                            # Создаем урок
                            new_lesson = Lesson(
                                teacher_name=cell_data['teacher'],
                                student_name=student_name,
                                subject=cell_data['subject'],
                                room="Cab 1", # По умолчанию, так как в CSV нет кабинета
                                start_time=start_time,
                                end_time=end_time,
                                source_file=filename
                            )
                            db.add(new_lesson)
                        except ValueError as e:
                            print(f"   ❌ Ошибка времени: {e}")

            db.commit()
            print(f"✅ {student_name}: Успешно")

        except Exception as e:
            print(f"❌ Ошибка файла {filename}: {e}")

if __name__ == "__main__":
    # Для ручного запуска
    db = SessionLocal()
    import_folder("uploads", db) # Папка uploads должна существовать
    db.close()