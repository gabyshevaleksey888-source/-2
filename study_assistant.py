import streamlit as st
import re
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Конспект-Мастер | Учеба с ИИ", page_icon="📚", layout="centered")

# --- ДИЗАЙН ---
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    h1 { color: #1D4ED8 !important; text-align: center; font-weight: 800; }
    .sub-title { text-align: center; color: #475569; font-size: 1.1rem; margin-bottom: 30px; }
    .stButton>button { 
        background: linear-gradient(90deg, #2563EB, #1D4ED8); 
        color: white; font-weight: bold; border-radius: 8px; width: 100%; padding: 12px;
    }
    .result-box {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- ПРОВЕРКА КЛЮЧА ---
api_key = st.secrets.get("PROXYAPI_KEY", "")
if not api_key:
    st.error("Ошибка: Ключ PROXYAPI_KEY не найден в Secrets.")
    st.stop()

client = OpenAI(base_url="https://api.proxyapi.ru/v1", api_key=api_key)

# --- ФУНКЦИИ ИЗВЛЕЧЕНИЯ ТЕКСТА ---
def get_youtube_transcript(url):
    # Извлекаем ID видео из ссылки
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if not video_id_match:
        return None, "Неверная ссылка на YouTube"
    
    video_id = video_id_match.group(1)
    try:
        # Пытаемся получить русские субтитры, если нет — английские
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['ru'])
        except:
            transcript = transcript_list.find_generated_transcript(['en'])
            
        transcript_data = transcript.fetch()
        full_text = " ".join([t['text'] for t in transcript_data])
        return full_text, None
    except TranscriptsDisabled:
        return None, "У этого видео отключены субтитры."
    except NoTranscriptFound:
        return None, "У этого видео нет доступных субтитров."
    except Exception as e:
        return None, f"Ошибка YouTube: {e}"

def get_article_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None, "Не удалось скачать страницу."
        text = trafilatura.extract(downloaded)
        if not text:
            return None, "Не удалось найти текст на странице."
        return text, None
    except Exception as e:
        return None, f"Ошибка сайта: {e}"

# --- ИНТЕРФЕЙС ---
st.markdown("<h1>📚 Конспект-Мастер</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Превратите часовое видео или длинную статью в краткий конспект и тест за 10 секунд.</p>", unsafe_allow_html=True)

url_input = st.text_input("Вставьте ссылку на YouTube-видео или статью:", placeholder="https://www.youtube.com/watch?v=... или https://habr.com/...")

if st.button("✨ Сделать конспект"):
    if not url_input:
        st.warning("Пожалуйста, вставьте ссылку.")
    else:
        with st.spinner("📥 Скачиваю и читаю текст..."):
            if "youtube.com" in url_input or "youtu.be" in url_input:
                text, error = get_youtube_transcript(url_input)
            else:
                text, error = get_article_text(url_input)
                
        if error:
            st.error(error)
            st.info("💡 Попробуйте вставить текст вручную в поле ниже.")
            manual_text = st.text_area("Вставьте текст для конспекта здесь:", height=200)
            if manual_text and st.button("Сделать конспект из текста"):
                text = manual_text
            else:
                st.stop()
                
        if text:
            # Ограничиваем текст, чтобы не превысить лимиты API (первые 30 000 символов)
            text = text[:30000] 
            
            with st.spinner("🧠 Нейросеть анализирует текст и пишет конспект..."):
                prompt = f"""Ты профессиональный студент-отличник. Сделай краткий и понятный конспект следующего текста. 
                Выдели 5 самых главных тезисов. Пиши четко, структурированно, без воды.
                
                Текст:
                {text}
                """
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.5
                    )
                    summary = response.choices[0].message.content
                    
                    st.markdown("<div class='result-box'>", unsafe_allow_html=True)
                    st.subheader("📝 Ваш конспект:")
                    st.markdown(summary)
                    
                    # Генерация теста
                    st.markdown("---")
                    st.subheader("🧠 Проверь себя (3 вопроса):")
                    quiz_prompt = f"На основе этого текста составь 3 интересных вопроса для проверки знаний (без ответов). Текст: {text[:10000]}"
                    quiz_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": quiz_prompt}],
                        temperature=0.7
                    )
                    st.markdown(quiz_response.choices[0].message.content)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Ошибка нейросети: {e}")
