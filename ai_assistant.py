import streamlit as st
import fitz  # PyMuPDF
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="DocuMind AI | Умный анализ документов", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# --- КАСТОМНЫЙ ДИЗАЙН (CSS) ---
st.markdown("""
<style>
    /* Главный заголовок */
    .main-title { font-size: 3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0; }
    .sub-title { font-size: 1.2rem; color: #4B5563; margin-bottom: 2rem; }
    
    /* Стили для карточек */
    .feature-card { background-color: #F3F4F6; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .feature-card h4 { margin-top: 0; color: #1F2937; }
    
    /* Кнопка */
    .stButton>button { background-color: #2563EB; color: white; border-radius: 8px; font-weight: 600; padding: 10px 20px; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1D4ED8; transform: translateY(-2px); }
    
    /* Сайдбар */
    .css-1d391kg { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- ПРОВЕРКА КЛЮЧА ---
api_key = st.secrets.get("PROXYAPI_KEY", "")
if not api_key:
    st.error("Ошибка: Ключ PROXYAPI_KEY не найден в Secrets.")
    st.stop()

try:
    api_key.encode('ascii')
except UnicodeEncodeError:
    st.error("⚠️ В API-ключе есть недопустимые символы (русские буквы). Проверьте Secrets.")
    st.stop()

client = OpenAI(base_url="https://api.proxyapi.ru/v1", api_key=api_key)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def split_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def get_embedding(text):
    response = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_chunks" not in st.session_state:
    st.session_state.document_chunks = []
if "document_embeddings" not in st.session_state:
    st.session_state.document_embeddings = []
if "doc_name" not in st.session_state:
    st.session_state.doc_name = ""

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8649/8649592.png", width=80) # Иконка
    st.title("Управление")
    st.info("1. Загрузите ваш PDF-документ\n2. Нажмите 'Обработать'\n3. Общайтесь с ИИ в чате!")
    
    uploaded_file = st.file_uploader("Выберите PDF файл", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("🚀 Обработать документ", type="primary", use_container_width=True):
            with st.spinner("🧠 ИИ читает и анализирует документ..."):
                try:
                    pdf_bytes = uploaded_file.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text() + "\n"
                    
                    st.session_state.document_chunks = split_text(full_text)
                    
                    if len(st.session_state.document_chunks) == 0:
                        st.error("Не удалось извлечь текст. Возможно, это скан-копия.")
                    else:
                        embeddings = []
                        for chunk in st.session_state.document_chunks:
                            embeddings.append(get_embedding(chunk))
                            
                        st.session_state.document_embeddings = embeddings
                        st.session_state.doc_name = uploaded_file.name
                        st.session_state.messages = [] # Очищаем чат для нового документа
                        st.success(f"✅ Готово! Документ «{uploaded_file.name}» обработан.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                    
    if st.session_state.doc_name:
        st.markdown("---")
        st.write(f"**Текущий документ:**\n📄 {st.session_state.doc_name}")
        if st.button("🗑️ Сбросить и загрузить другой", use_container_width=True):
            st.session_state.document_chunks = []
            st.session_state.document_embeddings = []
            st.session_state.messages = []
            st.session_state.doc_name = ""
            st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if not st.session_state.document_chunks:
    # Приветственный экран (Лендинг)
    st.markdown("<h1 class='main-title'>DocuMind AI 🧠</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Ваш личный ИИ-юрист, бухгалтер и аналитик. Загрузите любой PDF и задавайте вопросы по его содержанию.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='feature-card'><h4>📄 Любые PDF</h4><p>Договоры, инструкции, отчеты, научные статьи — ИИ прочитает всё.</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='feature-card'><h4>⚡ Мгновенно</h4><p>Не нужно читать 100 страниц. Задайте вопрос и получите точный ответ за секунды.</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='feature-card'><h4>🔒 Приватность</h4><p>Мы не сохраняем ваши документы. Вся работа происходит в оперативной памяти.</p></div>", unsafe_allow_html=True)
        
    st.info("👈 **Для начала работы загрузите PDF-документ в боковой панели слева.**")

else:
    # Экран чата
    st.markdown(f"<h2 class='main-title'>Работа с документом: {st.session_state.doc_name}</h2>", unsafe_allow_html=True)
    
    # Отображение истории чата
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Поле ввода
    if prompt := st.chat_input("Задайте вопрос по документу..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🔍 Ищу ответ в тексте..."):
                question_embedding = get_embedding(prompt)
                
                similarities = cosine_similarity(
                    [question_embedding], 
                    st.session_state.document_embeddings
                )[0]
                
                top_indices = np.argsort(similarities)[-3:][::-1]
                context = "\n\n".join([st.session_state.document_chunks[i] for i in top_indices])
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[
                        {"role": "system", "content": f"Ты профессиональный AI-ассистент. Отвечай на вопрос пользователя, используя ТОЛЬКО предоставленный контекст. Если ответа нет, так и скажи. Контекст:\n{context}"},
                        {"role": "user", "content": prompt}
                    ]
                )
                answer = response.choices[0].message.content
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
