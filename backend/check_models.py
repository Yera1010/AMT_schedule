import google.generativeai as genai

# 👇 ВСТАВЬ СВОЙ КЛЮЧ
API_KEY = "AIzaSyDjHC2-LYATSqmSr8DKXEjUJqZ80hK56Gk"

genai.configure(api_key=API_KEY)

print("🔍 Ищу доступные модели...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
except Exception as e:
    print(f"❌ Ошибка: {e}")