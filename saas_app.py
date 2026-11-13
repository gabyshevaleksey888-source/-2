import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="MortgagePro | Умная ипотека", layout="wide")

# --- 1. СИМУЛЯЦИЯ ПОЛЬЗОВАТЕЛЯ (В реальности здесь была бы база данных) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.premium = False
    st.session_state.saved_scenarios = []

st.sidebar.title("👤 Личный кабинет")

if not st.session_state.logged_in:
    st.sidebar.subheader("Вход в систему")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Пароль", type="password")
    if st.sidebar.button("Войти / Зарегистрироваться"):
        st.session_state.logged_in = True
        st.sidebar.success(f"Добро пожаловать, {email}!")
        st.rerun()
else:
    st.sidebar.success("Вы авторизованы")
    # Симулятор оплаты подписки
    st.session_state.premium = st.sidebar.toggle("💎 Включить Премиум-доступ (Симуляция)", value=st.session_state.premium)
    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()

# --- 2. ИНТЕРФЕЙС КАЛЬКУЛЯТОРА ---
st.title("🏠 MortgagePro")
st.write("Профессиональный расчет ипотеки с сохранением сценариев.")

# Вкладки
tab1, tab2, tab3 = st.tabs(["🧮 Калькулятор", "💾 Мои сценарии", "💎 Премиум функции"])

with tab1:
    col_input, col_results = st.columns([1, 2])
    
    with col_input:
        st.subheader("Параметры")
        total_cost = st.number_input("Стоимость (₽)", min_value=100000, max_value=100000000, value=5000000, step=100000)
        initial_payment = st.number_input("Первый взнос (₽)", min_value=0, max_value=total_cost, value=1000000, step=50000)
        rate = st.number_input("Ставка (%)", min_value=0.1, max_value=50.0, value=12.0, step=0.1)
        years = st.slider("Срок (лет)", 1, 30, 20)
        
        st.markdown("---")
        early_payment = st.number_input("Досрочный платеж (₽/мес)", min_value=0, value=0, step=5000)
        early_strategy = st.radio("Стратегия досрочного погашения:", ("Уменьшать срок", "Уменьшать платеж"))
        
        calc_btn = st.button("Рассчитать", type="primary", use_container_width=True)

    loan_amount = total_cost - initial_payment
    
    if calc_btn or 'calc_results' in st.session_state:
        if loan_amount <= 0:
            st.warning("Кредит не нужен!")
        else:
            monthly_rate = rate / 100 / 12
            n_months = years * 12
            
            if monthly_rate > 0:
                monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1)
            else:
                monthly_payment = loan_amount / n_months

            balance = loan_amount
            total_interest = 0
            schedule = []
            months_actual = 0
            
            for month in range(1, n_months * 2 + 1):
                if balance <= 0:
                    break
                interest = balance * monthly_rate
                
                if early_strategy == "Уменьшать платеж" and early_payment > 0 and month > 1:
                    rem_months = n_months - month + 1
                    if monthly_rate > 0:
                        monthly_payment = balance * (monthly_rate * (1 + monthly_rate)**rem_months) / ((1 + monthly_rate)**rem_months - 1)
                    else:
                        monthly_payment = balance / rem_months
                        
                principal = monthly_payment - interest
                if principal + early_payment >= balance:
                    principal = balance - early_payment
                    if principal < 0: principal = 0
                    
                balance = balance - principal - early_payment
                total_interest += interest
                
                schedule.append({
                    "Месяц": month, "Год": (month - 1) // 12 + 1,
                    "Остаток долга": max(0, balance),
                    "Проценты": total_interest,
                })
                months_actual = month

            df = pd.DataFrame(schedule)
            st.session_state.calc_results = {
                "loan": loan_amount, "payment": monthly_payment, "interest": total_interest,
                "actual_months": months_actual, "df": df
            }
            
            with col_results:
                st.subheader("Результаты")
                c1, c2, c3 = st.columns(3)
                c1.metric("Платеж", f"{monthly_payment:,.0f} ₽".replace(",", " "))
                c2.metric("Переплата", f"{total_interest:,.0f} ₽".replace(",", " "))
                c3.metric("Срок", f"{months_actual//12} г. {months_actual%12} мес.")
                
                if early_payment > 0 and months_actual < n_months:
                    st.success(f"Вы сэкономите {n_months - months_actual} месяцев!")

                # График Plotly
                fig = px.area(df, x="Месяц", y="Остаток долга", title="График погашения долга")
                fig.update_layout(yaxis_title="Остаток (₽)", xaxis_title="Месяц")
                st.plotly_chart(fig, use_container_width=True)

                # Кнопка сохранения сценария (SaaS-фишка)
                if st.session_state.logged_in:
                    if st.button("💾 Сохранить этот сценарий"):
                        st.session_state.saved_scenarios.append({
                            "Стоимость": total_cost, "Платеж": monthly_payment, 
                            "Переплата": total_interest, "Срок_мес": months_actual
                        })
                        st.toast("Сценарий сохранен в личном кабинете!")
                else:
                    st.info("Войдите в личный кабинет, чтобы сохранять сценарии.")

with tab2:
    st.subheader("Мои сохраненные расчеты")
    if not st.session_state.logged_in:
        st.warning("Пожалуйста, войдите в систему слева.")
    elif len(st.session_state.saved_scenarios) == 0:
        st.write("У вас пока нет сохраненных сценариев.")
    else:
        for i, sc in enumerate(st.session_state.saved_scenarios):
            st.write(f"**Сценарий {i+1}:** Квартира за {sc['Стоимость']:,.0f} ₽ | Платеж: {sc['Платеж']:,.0f} ₽ | Переплата: {sc['Переплата']:,.0f} ₽")
        if st.button("Очистить историю"):
            st.session_state.saved_scenarios = []
            st.rerun()

with tab3:
    st.subheader("💎 Премиум возможности")
    if not st.session_state.premium:
        st.info("Вы находитесь на базовом тарифе (Free).")
        st.write("В Премиум-тарифе доступно:")
        st.write("- 📥 Экспорт графика платежей в Excel (для банка)")
        st.write("- 📊 Сравнение 3-х сценариев одновременно")
        st.write("- 📉 Учет инфляции")
        st.button("Подключить Премиум за 199 ₽/мес (Симуляция)", type="primary")
    else:
        st.success("Премиум-доступ активирован!")
        if 'calc_results' in st.session_state:
            # Экспорт данных
            csv = st.session_state.calc_results['df'].to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Скачать график платежей (Excel/CSV)",
                data=csv,
                file_name='grafik_platezhey.csv',
                mime='text/csv',
                type="primary"
            )
        else:
            st.write("Сначала сделайте расчет во вкладке 'Калькулятор'.")
