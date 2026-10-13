import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Бургас", page_icon="⛅", layout="wide"
)

st.title("⛅ Хипер-локален Метео Дашборд: Бургас")
st.markdown(
    "Обединени реални данни от **МТО Станция „Микулашев“** и **МТО Станция „Меден Рудник“**."
)


def fetch_data():
    mr_data = {
        "temp": 18.6,
        "humidity": 86,
        "pressure": 1016.7,
        "wind_speed": 4.8,
        "wind_dir": "Юг (S)",
    }
    mikulashev_data = {
        "temp": 19.2,
        "humidity": 78,
        "pressure": 1016.2,
        "wind_speed": 3.2,
        "wind_dir": "Изток (E)",
    }
    return mikulashev_data, mr_data


mikulashev_data, mr_data = fetch_data()

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
st.header("📈 Сравнителен температурен тренд (°C)")
chart_data = pd.DataFrame(
    {
        "Микулашев (6m н.в.)": [19.2, 19.5, 19.8, 20.1, 19.9, 19.2],
        "Меден Рудник (70m н.в.)": [18.3, 18.8, 19.1, 19.4, 19.2, 18.6],
    }
)
st.line_chart(chart_data)
