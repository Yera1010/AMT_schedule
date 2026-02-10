from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

URL_DATABASE = 'sqlite:///./lessons.db'

engine = create_engine(URL_DATABASE, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    teacher_name = Column(String, index=True) # Например: Adina
    student_name = Column(String, index=True) # Например: Madina
    subject = Column(String)   
    room = Column(String, default="Cab 1")               
    start_time = Column(DateTime)             # 2026-02-04 09:00:00
    end_time = Column(DateTime)               # 2026-02-04 10:30:00
    source_file = Column(String)              # Чтобы знать, откуда пришла запись

# Создаем таблицы
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ База данных создана успешно!")