import google.generativeai as genai
import os

# ==========================================
# ВСТАВЬ СЮДА КЛЮЧ
raw_key = "AIzaSyAsXzK3UVhFxcupprXRZdlHJJJIDsSdEqc"
# ==========================================

# Применяем наш "патч" для стабильности
api_key = raw_key.strip()
genai.configure(api_key=api_key, transport="rest")

print(f"🔑 Использую ключ: {api_key[:5]}...{api_key[-3:]}")
print("📡 Спрашиваю у Google список доступных моделей...")

try:
    count = 0
    for m in genai.list_models():
        # Нам нужны только те модели, которые умеют генерировать текст (generateContent)
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ НАЙДЕНА: {m.name}")
            count += 1
            
    if count == 0:
        print("⚠️ Список пуст. Возможно, API ключ не имеет доступа к моделям.")
    else:
        print(f"\n🎉 Всего доступно моделей: {count}")
        print("Скопируй любое название (например, models/gemini-pro) и пришли в чат.")

except Exception as e:
    print(f"❌ ОШИБКА: {e}")