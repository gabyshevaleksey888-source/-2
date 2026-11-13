import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from supabase import create_client, Client

st.set_page_config(page_title="MortgagePro | Умная ипотека", layout="wide")

# --- 1. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- 2. АВТОРИЗАЦИЯ (упрощенная) ---
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

st.sidebar.title("👤 Личный кабинет")

if not st.session_state.user_email:
    st.sidebar.subheader("Вход в систему")
    email_input = st.sidebar.text_input("Введите ваш Email")
    if st.sidebar.button("Войти"):
        if "@" in email_input:
            st.session_state.user_email = email_input
            st.sidebar.success(f"Привет, {email_input}!")
            st.rerun()
        else:
            st.sidebar.error("Введите корректный Email (с @)")
else:
    st.sidebar.success(f"Вы вошли как:\n**{st.session_state.user_email}**")
    if st.sidebar.button("Выйти"):
        st.session_state.user_email = None
        st.rerun()

# --- 3. ИНТЕРФЕЙС ---
st.title("🏠 MortgagePro")
tab1, tab2 = st.tabs(["🧮 Калькулятор", "💾 Мои сценарии"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Параметры")
        total_cost = st.number_input("Стоимость (₽)", min_value=100000, value=5000000, step=100000)
        initial_payment = st.number_input("Первый взнос (₽)", min_value=0, max_value=total_cost, value=1000000, step=50000)
        rate = st.number_input("Ставка (%)", min_value=0.1, value=12.0, step=0.1)
        years = st.slider("Срок (лет)", 1, 30, 20)
        early_payment = st.number_input("Досрочный платеж (₽/мес)", min_value=0, value=0, step=5000)
        early_strategy = st.radio("Стратегия:", ("Уменьшать срок", "Уменьшать платеж"))
        calc_btn = st.button("Рассчитать", type="primary", use_container_width=True)

    loan_amount = total_cost - initial_payment
    
    if calc_btn:
        if loan_amount <= 0:
            st.warning("Кредит не нужен!")
        else:
            monthly_rate = rate / 100 / 12
            n_months = years * 12
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1) if monthly_rate > 0 else loan_amount / n_months
            
            balance = loan_amount
            total_interest = 0
            schedule = []
            months_actual = 0
            
            for month in range(1, n_months * 2 + 1):
                if balance <= 0: break
                interest = balance * monthly_rate
                
                if early_strategy == "Уменьшать платеж" and early_payment > 0 and month > 1:
                    rem_months = n_months - month + 1
                    monthly_payment = balance * (monthly_rate * (1 + monthly_rate)**rem_months) / ((1 + monthly_rate)**rem_months - 1) if monthly_rate > 0 else balance / rem_months
                        
                principal = monthly_payment - interest
                if principal + early_payment >= balance:
                    principal = balance - early_payment
                    if principal < 0: principal = 0
                    
                balance = balance - principal - early_payment
                total_interest += interest
                
                schedule.append({"Месяц": month, "Остаток долга": max(0, balance)})
                months_actual = month

            df = pd.DataFrame(schedule)
            
            with col2:
                st.subheader("Результаты")
                c1, c2, c3 = st.columns(3)
                c1.metric("Платеж", f"{monthly_payment:,.0f} ₽".replace(",", " "))
                c2.metric("Переплата", f"{total_interest:,.0f} ₽".replace(",", " "))
                c3.metric("Срок", f"{months_actual//12} г. {months_actual%12} мес.")
                
                fig = px.area(df, x="Месяц", y="Остаток долга", title="График погашения долга")
                st.plotly_chart(fig, use_container_width=True)

                if st.session_state.user_email:
                    if st.button("💾 Сохранить этот расчет в базу", type="primary"):
                        # Отправляем данные в Supabase
                        data = {
                            "user_email": st.session_state.user_email,
                            "total_cost": total_cost,
                            "monthly_payment": round(monthly_payment, 2),
                            "total_interest": round(total_interest, 2),
                            "months_actual": months_actual
                        }
                        try:
                            supabase.table("scenarios").insert(data).execute()
                            st.success("Сценарий успешно сохранен в облачную базу данных!")
                        except Exception as e:
                            st.error(f"Ошибка сохранения: {e}")
                else:
                    st.info("Войдите слева, чтобы сохранять сценарии.")

with tab2:
    st.subheader("Мои сохраненные расчеты (из Базы Данных)")
    if not st.session_state.user_email:
        st.warning("Пожалуйста, войдите в систему.")
    else:
        # Запрашиваем данные из Supabase
        try:
            response = supabase.table("scenarios").select("*").eq("user_email", st.session_state.user_email).order("created_at", desc=True).execute()
            
            if response.data:
                df_db = pd.DataFrame(response.data)
                df_db = df_db.rename(columns={
                    "total_cost": "Стоимость", "monthly_payment": "Платеж", 
                    "total_interest": "Переплата", "months_actual": "Срок (мес)"
                })
                st.dataframe(df_db[["Стоимость", "Платеж", "Переплата", "Срок (мес)"]])
            else:
                st.write("У вас пока нет сохраненных сценариев в базе.")
        except Exception as e:
            st.error(f"Ошибка чтения из базы: {e}")
