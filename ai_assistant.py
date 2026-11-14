import streamlit as st
import fitz  # PyMuPDF
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

st.set_page_config(page_title="AI Document Assistant", layout="wide")
st.title("📄 AI-Ассистент по документам")
st.write("Загрузите PDF, и я отвечу на вопросы по его содержанию (работает без VPN).")

# --- ПРОВЕРКА КЛЮЧА НА РУССКИЕ БУКВЫ ---
api_key = st.secrets.get("PROXYAPI_KEY", "")
if not api_key:
    st.error("Ошибка: Ключ PROXYAPI_KEY не найден в Secrets.")
    st.stop()

try:
    # Проверяем, что в ключе только английские символы (ASCII)
    api_key.encode('ascii')
except UnicodeEncodeError:
    st.error("⚠️ В вашем API-ключе есть русские буквы или лишние символы! Пожалуйста, зайдите в Secrets и скопируйте ключ заново, внимательно проверяя каждую букву.")
    st.stop()

# Настройка клиента ProxyAPI
try:
    client = OpenAI(
        base_url="https://api.proxyapi.ru/v1", 
        api_key=api_key,
    )
except Exception as e:
    st.error(f"Ошибка инициализации клиента: {e}")
    st.stop()

# Функция для разбивки текста на куски
def split_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# Функция для получения эмбеддингов
def get_embedding(text):
    response = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Инициализация сессии
if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_chunks" not in st.session_state:
    st.session_state.document_chunks = []
if "document_embeddings" not in st.session_state:
    st.session_state.document_embeddings = []

# Боковая панель
with st.sidebar:
    st.header("Загрузка документа")
    uploaded_file = st.file_uploader("Выберите PDF файл", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Обработать документ", type="primary"):
            with st.spinner("Читаю и анализирую документ..."):
                try:
                    # Читаем файл
                    pdf_bytes = uploaded_file.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text() + "\n"
                    
                    st.session_state.document_chunks = split_text(full_text)
                    
                    if len(st.session_state.document_chunks) == 0:
                        st.error("Не удалось извлечь текст из этого PDF. Возможно, он состоит только из картинок (сканов).")
                        st.stop()
                    
                    # Векторизуем
                    embeddings = []
                    for chunk in st.session_state.document_chunks:
                        embeddings.append(get_embedding(chunk))
                        
                    st.session_state.document_embeddings = embeddings
                    
                    st.success(f"Готово! Разбит на {len(st.session_state.document_chunks)} фрагментов.")
                    st.session_state.messages = []
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# Основной чат
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Задайте вопрос по документу..."):
    if not st.session_state.document_chunks:
        st.warning("Сначала загрузите и обработайте PDF в боковой панели!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Ищу ответ..."):
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
                        {"role": "system", "content": f"Отвечай на вопрос, используя ТОЛЬКО этот контекст:\n{context}"},
                        {"role": "user", "content": prompt}
                    ]
                )
                answer = response.choices[0].message.content
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
