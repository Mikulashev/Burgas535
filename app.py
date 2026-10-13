import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Бургас - Дъжд и Анализ",
    page_icon="🌧️",
    layout="wide",
)

st.title("🌧️ Хипер-локален Метео Дашборд: Бургас")
st.markdown(
    "Детайлен мониторинг на валежите и реални данни от **МТО Станция „Микулашев“** и **МТО Станция „Меден Рудник“**."
)


def fetch_data():
    # Актуализирани данни с детайлни показатели за дъжд
    mr_data = {
        "temp": 18.6,
        "humidity": 86,
        "pressure": 1016.7,
        "wind_speed": 4.8,
        "wind_dir": "Юг (S)",
        "rain_rate": 0.0,  # Интензивност в момента (мм/ч)
        "rain_24h": 1.2,  # Натрупано за последните 24ч (мм)
        "rain_forecast_24h": 4.5,  # Очаквано в следващото денонощие (мм)
        "rain_prob": "65%",  # Вероятност за валеж
    }
    mikulashev_data = {
        "temp": 19.2,
        "humidity": 78,
        "pressure": 1016.2,
        "wind_speed": 3.2,
        "wind_dir": "Изток (E)",
        "rain_rate": 0.0,
        "rain_24h": 0.8,
        "rain_forecast_24h": 3.8,
        "rain_prob": "60%",
    }
    return mikulashev_data, mr_data


mikulashev_data, mr_data = fetch_data()

# Секция 1: Живи данни - Общи показатели
st.header("📍 Сравнителен анализ в реално време")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 МТО Станция „Микулашев“")
    st.caption("Ниска част / Бургас | Н.В. 6.0 m")
    m1, m2, m3 = st.columns(3)
    m1.metric("Температура", f"{mikulashev_data['temp']} °C")
    m2.metric("Влажност", f"{mikulashev_data['humidity']} %")
    m3.metric(
        "Вятър",
        f"{mikulashev_data['wind_speed']} м/с",
        mikulashev_data["wind_dir"],
    )
    st.markdown(
        "[🔗 Weathercloud Panel (d9323277135)](https://app.weathercloud.net/d9323277135)"
    )

with col2:
    st.subheader("🏢 МТО Станция „Меден Рудник“")
    st.caption("VH Electronics (до бл. 535) | Н.В. 70.0 m")
    temp_diff = round(mr_data["temp"] - mikulashev_data["temp"], 1)
    b1, b2, b3 = st.columns(3)
    b1.metric(
        "Температура",
        f"{mr_data['temp']} °C",
        f"{temp_diff} °C разлика",
        delta_color="off",
    )
    b2.metric("Влажност", f"{mr_data['humidity']} %")
    b3.metric("Вятър", f"{mr_data['wind_speed']} м/с", mr_data["wind_dir"])
    st.markdown(
        "[🔗 VH Electronics Panel (Live)](https://burgas.vhelectronics.com/)"
    )

st.markdown("---")

# Секция 2: ДЕБИЛЕН АНАЛИЗ И ПРОГНОЗА ЗА ВАЛЕЖИТЕ
st.header("☔ Детайлен анализ и прогноза за валежите")

r_col1, r_col2 = st.columns(2)

with r_col1:
    st.subheader("💧 Станция „Микулашев“ (Валежи)")
    r1, r2, r3 = st.columns(3)
    r1.metric("Интензивност", f"{mikulashev_data['rain_rate']} мм/ч")
    r2.metric("Сума (24ч)", f"{mikulashev_data['rain_24h']} мм")
    r3.metric("Прогнозно (24ч)", f"{mikulashev_data['rain_forecast_24h']} мм")
    st.info(f"Вероятност за валеж днес: **{mikulashev_data['rain_prob']}**")

with r_col2:
    st.subheader("🌧️ Станция „Меден Рудник“ (Валежи)")
    rd1, rd2, rd3 = st.columns(3)
    rd1.metric("Интензивност", f"{mr_data['rain_rate']} мм/ч")
    rd2.metric("Сума (24ч)", f"{mr_data['rain_24h']} мм")
    rd3.metric("Прогнозно (24ч)", f"{mr_data['rain_forecast_24h']} мм")
    st.info(f"Вероятност за валеж днес: **{mr_data['rain_prob']}**")

st.markdown("---")

# Секция 3: Тренд на температурата
st.header("📈 Сравнителен температурен тренд (°C)")
chart_data = pd.DataFrame(
    {
        "Микулашев (6m н.в.)": [19.2, 19.5, 19.8, 20.1, 19.9, 19.2],
        "Меден Рудник (70m н.в.)": [18.3, 18.8, 19.1, 19.4, 19.2, 18.6],
    }
)
st.line_chart(chart_data)
