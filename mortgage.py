import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Ипотечный калькулятор", layout="wide")

st.title("🏠 Умный ипотечный калькулятор")
st.write("Рассчитайте ежемесячный платеж, переплату и посмотрите, как быстро вы сможете закрыть кредит.")

# Боковая панель с настройками
st.sidebar.header("Параметры кредита")

# Ввод данных
total_cost = st.sidebar.number_input("Стоимость недвижимости (₽)", min_value=100000, max_value=100000000, value=5000000, step=100000)
initial_payment = st.sidebar.number_input("Первоначальный взнос (₽)", min_value=0, max_value=total_cost, value=1000000, step=50000)
loan_amount = total_cost - initial_payment

rate = st.sidebar.number_input("Процентная ставка (% годовых)", min_value=0.1, max_value=50.0, value=12.0, step=0.1)
years = st.sidebar.slider("Срок ипотеки (лет)", min_value=1, max_value=30, value=20)

st.sidebar.subheader("Досрочное погашение")
early_payment = st.sidebar.number_input("Досрочный платеж в месяц (₽)", min_value=0, max_value=1000000, value=0, step=10000)
early_strategy = st.sidebar.radio(
    "Стратегия досрочного погашения:",
    ("Уменьшать срок", "Уменьшать платеж")
)

# Расчет
if loan_amount <= 0:
    st.warning("Первоначальный взнос равен или больше стоимости недвижимости. Кредит не нужен!")
else:
    monthly_rate = rate / 100 / 12
    n_months = years * 12
    
    # Стандартная аннуитетная формула
    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1)
    else:
        monthly_payment = loan_amount / n_months

    # Симуляция графика платежей (для учета досрочных погашений)
    balance = loan_amount
    total_interest = 0
    total_paid = 0
    months_actual = 0
    
    schedule = []
    
    # Ограничим цикл, чтобы не уйти в бесконечность
    max_iterations = n_months * 2 
    
    for month in range(1, max_iterations + 1):
        if balance <= 0:
            break
            
        interest = balance * monthly_rate
        
        # Если стратегия - уменьшать платеж, мы пересчитываем основной платеж
        if early_strategy == "Уменьшать платеж" and early_payment > 0 and month > 1:
            remaining_months = n_months - month + 1
            if monthly_rate > 0:
                monthly_payment = balance * (monthly_rate * (1 + monthly_rate)**remaining_months) / ((1 + monthly_rate)**remaining_months - 1)
            else:
                monthly_payment = balance / remaining_months
                
        principal = monthly_payment - interest
        
        # Если это последний платеж или платеж больше остатка
        if principal + early_payment >= balance:
            principal = balance - early_payment
            if principal < 0: principal = 0
            
        balance = balance - principal - early_payment
        total_interest += interest
        total_paid += interest + principal + early_payment
        
        # Записываем в график (каждый месяц)
        schedule.append({
            "Месяц": month,
            "Год": (month - 1) // 12 + 1,
            "Остаток долга": max(0, balance),
            "Выплачено процентов": total_interest,
            "Выплачено тела кредита": total_paid - total_interest
        })
        months_actual = month

    actual_years = months_actual // 12
    actual_months = months_actual % 12
    time_saved_months = n_months - months_actual

    # Вывод главных цифр
    col1, col2, col3 = st.columns(3)
    col1.metric("Сумма кредита", f"{loan_amount:,.0f} ₽".replace(",", " "))
    col2.metric("Ежемесячный платеж (базовый)", f"{monthly_payment:,.0f} ₽".replace(",", " "))
    col3.metric("Общая переплата", f"{total_interest:,.0f} ₽".replace(",", " "))

    if early_payment > 0:
        if time_saved_months > 0:
            st.success(f"🎉 Благодаря досрочным платежам вы закроете ипотеку на **{time_saved_months} месяцев** раньше! (Срок: {actual_years} г. {actual_months} мес.)")
        else:
            st.info(f"Срок кредита: {actual_years} лет и {actual_months} месяцев.")

    # Визуализация
    df = pd.DataFrame(schedule)
    
    st.subheader("Структура выплат")
    st.write("Красным — сколько вы отдадите банку (проценты), синим — сколько вернете за саму квартиру.")
    
    fig1, ax1 = plt.subplots(figsize=(8, 3))
    sizes = [total_paid - total_interest, total_interest]
    labels = ['Тело кредита', 'Проценты банку']
    colors = ['#1f77b4', '#d62728']
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 12})
    ax1.axis('equal')
    st.pyplot(fig1)

    st.subheader("График погашения долга")
    st.write("Здесь видно, как быстро уменьшается ваш долг перед банком.")
    
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(df["Месяц"], df["Остаток долга"], color='#d62728', linewidth=2)
    ax2.fill_between(df["Месяц"], df["Остаток долга"], color='#d62728', alpha=0.1)
    ax2.set_xlabel("Месяцы")
    ax2.set_ylabel("Остаток долга (₽)")
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Убираем научный формат чисел на оси Y
    ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',').replace(',', ' ')))
    st.pyplot(fig2)

    with st.expander("Посмотреть подробную таблицу платежей"):
        st.dataframe(df.style.format("{:,.0f}"))
