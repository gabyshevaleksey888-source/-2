import streamlit as st
from PIL import Image
import io

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(
    page_title="Сжатие фото | Госуслуги и документы", 
    page_icon="🖼️", 
    layout="centered"
)

# --- ДИЗАЙН ---
st.markdown("""
<style>
    .stApp { background-color: #F0FDF4; } /* Приятный светло-зеленый фон */
    h1 { color: #166534 !important; text-align: center; }
    .sub-title { text-align: center; color: #4B5563; font-size: 1.2rem; margin-bottom: 30px;}
    .ad-placeholder { 
        background-color: #FEF3C7; border: 2px dashed #F59E0B; 
        padding: 20px; text-align: center; color: #B45309; 
        border-radius: 10px; margin: 20px 0; font-weight: bold;
    }
    .stButton>button { 
        background: linear-gradient(90deg, #16A34A, #15803D); 
        color: white; font-weight: bold; border-radius: 8px; width: 100%; padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- ГЛАВНЫЙ ЭКРАН ---
st.markdown("<h1>📸 Сжатие фото для документов</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Уменьшите размер фото до нужного (100, 300, 500 КБ) без потери качества. Идеально для Госуслуг, виз и резюме.</p>", unsafe_allow_html=True)

# Имитация рекламного блока (Верхний баннер)
st.markdown("<div class='ad-placeholder'>[Здесь будет ваша реклама (Google AdSense) для монетизации]</div>", unsafe_allow_html=True)

# --- ИНТЕРФЕЙС ---
uploaded_file = st.file_uploader("Загрузите фото (JPG, PNG)", type=["jpg", "jpeg", "png"])

target_size_kb = st.select_slider(
    "Выберите максимальный размер файла:",
    options=[50, 100, 200, 300, 500, 1024],
    value=300
)

if uploaded_file is not None:
    # Читаем картинку
    img = Image.open(uploaded_file)
    
    # Переводим в RGB, если это PNG с прозрачностью (для JPEG это важно)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    # Показываем оригинал
    original_size = len(uploaded_file.getvalue()) / 1024
    st.info(f"📄 Оригинал: {original_size:.0f} КБ | Разрешение: {img.width}x{img.height}")

    if st.button("🚀 Сжать фото"):
        with st.spinner("Магия сжатия..."):
            # Алгоритм подбора качества
            quality = 95
            target_bytes = target_size_kb * 1024
            output_buffer = io.BytesIO()
            
            # Сохраняем в цикле, пока не достигнем нужного размера
            while quality > 10:
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="JPEG", quality=quality)
                size = output_buffer.tell()
                
                if size <= target_bytes:
                    break
                quality -= 5 # Если файл все еще большой, уменьшаем качество
            
            # Если даже при низком качестве файл слишком большой, уменьшаем разрешение
            if output_buffer.tell() > target_bytes:
                scale = 0.9
                while output_buffer.tell() > target_bytes and img.width > 200:
                    new_w = int(img.width * scale)
                    new_h = int(img.height * scale)
                    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    output_buffer = io.BytesIO()
                    resized_img.save(output_buffer, format="JPEG", quality=85)
                    scale -= 0.1

            final_size = output_buffer.tell() / 1024
            st.success(f"✅ Готово! Итоговый размер: {final_size:.0f} КБ (Качество: {quality}%)")
            
            # Перемещаем курсор в начало буфера для скачивания
            output_buffer.seek(0)
            
            # Кнопка скачивания
            st.download_button(
                label="⬇️ Скачать сжатое фото",
                data=output_buffer,
                file_name=f"compressed_{uploaded_file.name}",
                mime="image/jpeg"
            )
            
            # Имитация рекламного блока (Нижний баннер)
            st.markdown("<div class='ad-placeholder'>[Здесь будет ваша реклама перед скачиванием]</div>", unsafe_allow_html=True)
