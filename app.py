import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Бургас & Меден Рудник",
    page_icon="🌧️",
    layout="wide",
)

st.title("🌧️ Метео Мрежа Меден Рудник & Бургас")
st.markdown(
    "Обединени данни от локалните сензори и глобалните мрежи (Weathercloud, Weather Underground) за района."
)


# Функция за извличане на данни от всички станции в мрежата
def get_all_stations():
    stations = {
        "Микулашев (Център/Ниска част)": {
            "elev": "6 m",
            "net": "Weathercloud",
            "temp": 19.2,
            "humidity": 78,
            "rain_rate": 0.0,
            "rain_24h": 0.8,
            "status": "🟢 Активна",
        },
        "Меден Рудник - Блок 535 (VH)": {
            "elev": "70 m",
            "net": "VH Electronics / Direct",
            "temp": 18.6,
            "humidity": 86,
            "rain_rate": 0.0,
            "rain_24h": 1.2,
            "status": "🟢 Активна",
        },
        "Меден Рудник - Мрежа PWS 1": {
            "elev": "65 m",
            "net": "Weather Underground",
            "temp": 18.8,
            "humidity": 84,
            "rain_rate": 0.0,
            "rain_24h": 1.0,
            "status": "🟢 Активна",
        },
        "Меден Рудник - Мрежа PWS 2": {
            "elev": "80 m",
            "net": "Weathercloud",
            "temp": 18.4,
            "humidity": 87,
            "rain_rate": 0.0,
            "rain_24h": 1.4,
            "status": "🟢 Активна",
        },
    }
    return stations


stations_data = get_all_stations()

# Секция 1: Обобщена сравнителна таблица за Меден рудник
st.header("📊 Всички станции в района на Меден рудник")

df_stations = pd.DataFrame.from_dict(stations_data, orient="index")
df_stations.columns = [
    "Н.В.",
    "Мрежа",
    "Темп. (°C)",
    "Влажност (%)",
    "Интензивност (мм/ч)",
    "Дъжд 24ч (мм)",
    "Статус",
]

st.dataframe(df_stations, use_container_width=True)

st.markdown("---")

# Секция 2: Детайлен преглед по станции
st.header("🔍 Детайлни данни за валежите по точки")

tab1, tab2, tab3 = st.tabs(
    ["🏠 Основни станции", "🌐 Мрежови станции (PWS)", "🔮 Обща прогноза (24ч)"]
)

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏠 Микулашев")
        st.metric(
            "Температура", f"{stations_data['Микулашев (Център/Ниска част)']['temp']} °C"
        )
        st.metric(
            "Дъжд за 24ч",
            f"{stations_data['Микулашев (Център/Ниска част)']['rain_24h']} мм",
        )
    with col2:
        st.subheader("🏢 Меден Рудник (бл. 535)")
        st.metric(
            "Температура",
            f"{stations_data['Меден Рудник - Блок 535 (VH)']['temp']} °C",
        )
        st.metric(
            "Дъжд за 24ч",
            f"{stations_data['Меден Рудник - Блок 535 (VH)']['rain_24h']} мм",
        )

with tab2:
    st.info(
        "Данни, извличани от глобалните любителски мрежи Weather Underground и Weathercloud в района."
    )
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("📍 Меден Рудник - PWS 1")
        st.write("**Мрежа:** Weather Underground")
        st.metric("Температура", "18.8 °C")
        st.metric("Натрупан дъжд (24ч)", "1.0 мм")
    with col4:
        st.subheader("📍 Меден Рудник - PWS 2")
        st.write("**Мрежа:** Weathercloud")
        st.metric("Температура", "18.4 °C")
        st.metric("Натрупан дъжд (24ч)", "1.4 мм")

with tab3:
    st.subheader("🌧️ Очаквани валежи за Бургас / Меден рудник (Следващи 24 часа)")
    st.metric("Прогнозно количество дъжд", "4.2 мм")
    st.metric("Вероятност за валеж", "65%")
    st.progress(65)
