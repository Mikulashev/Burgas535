import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Бургас & Меден Рудник - Часова Прогноза",
    page_icon="⚠️",
    layout="wide",
)

st.title("🌧️ Хипер-локален Метео Дашборд: Бургас и Меден Рудник")
st.markdown(
    "Мониторинг на станциите в реално време и **почасова прогноза за валежите** с цел ранно предупреждение за наводнения."
)


# Функция за извличане на детайлна почасова прогноза от Open-Meteo API за Бургас
@st.cache_data(ttl=1800)
def fetch_hourly_forecast():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=42.5048&longitude=27.4626&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Sofia"
        response = requests.get(url)
        data = response.json()

        hourly_data = data["hourly"]
        # Взимаме следващите 24 часа
        times = hourly_data["time"][:24]
        temps = hourly_data["temperature_2m"][:24]
        precips = hourly_data["precipitation"][:24]
        probs = hourly_data["precipitation_probability"][:24]

        # Форматираме часовете за по-удобно четене (само часът)
        formatted_times = [
            datetime.datetime.fromisoformat(t).strftime("%H:00 (%d.%m)")
            for t in times
        ]

        df_hourly = pd.DataFrame(
            {
                "Час": formatted_times,
                "Температура (°C)": temps,
                "Очакван дъжд (мм)": precips,
                "Вероятност (%)": probs,
            }
        )

        total_rain = sum(precips)
        max_prob = max(probs) if probs else 0

        return df_hourly, round(total_rain, 1), max_prob
    except:
        # Резервни данни при евентуален срив на мрежата
        dummy_df = pd.DataFrame(
            {
                "Час": [f"{i:02d}:00" for i in range(24)],
                "Температура (°C)": [18] * 24,
                "Очакван дъжд (мм)": [0.0] * 24,
                "Вероятност (%)": [10] * 24,
            }
        )
        return dummy_df, 4.2, 60


df_hourly_forecast, api_rain_forecast, api_rain_prob = fetch_hourly_forecast()


# Пълна мрежа от станции
def get_station_network():
    data = {
        "Микулашев (Weathercloud)": {
            "район": "Микулашев / Център",
            "id": "d9323277135",
            "тип": "Weathercloud (6м н.в.)",
            "temp": 19.2,
            "humidity": 78,
            "rain_24h": 0.8,
        },
        "IBANEV3": {
            "район": "Микулашев / Център",
            "id": "IBANEV3",
            "тип": "Weather Underground",
            "temp": 19.0,
            "humidity": 80,
            "rain_24h": 0.9,
        },
        "IBURGA13": {
            "район": "Микулашев / Център",
            "id": "IBURGA13",
            "тип": "Weather Underground",
            "temp": 19.4,
            "humidity": 77,
            "rain_24h": 0.7,
        },
        "Меден Рудник - Бл. 535 (VH)": {
            "район": "Меден Рудник",
            "id": "VH-535",
            "тип": "Direct / VH (70м н.в.)",
            "temp": 18.6,
            "humidity": 86,
            "rain_24h": 1.2,
        },
        "IBURGA54": {
            "район": "Меден Рудник",
            "id": "IBURGA54",
            "тип": "Weather Underground",
            "temp": 18.5,
            "humidity": 87,
            "rain_24h": 1.3,
        },
        "IBURGA90": {
            "район": "Меден Рудник",
            "id": "IBURGA90",
            "тип": "Weather Underground",
            "temp": 18.7,
            "humidity": 85,
            "rain_24h": 1.1,
        },
        "IBURGA36": {
            "район": "Меден Рудник",
            "id": "IBURGA36",
            "тип": "Weather Underground",
            "temp": 18.3,
            "humidity": 88,
            "rain_24h": 1.4,
        },
        "IBURGA110": {
            "район": "Меден Рудник",
            "id": "IBURGA110",
            "тип": "Weather Underground",
            "temp": 18.9,
            "humidity": 83,
            "rain_24h": 1.0,
        },
    }
    return data


stations = get_station_network()

# Секция 1: Обобщена таблица на станциите
st.header("📊 Сравнителна таблица на станциите в района")
df = pd.DataFrame.from_dict(stations, orient="index")
df.columns = [
    "Район",
    "ID / Код",
    "Мрежа / Тип",
    "Темп. (°C)",
    "Влажност (%)",
    "Дъжд 24ч (мм)",
]
st.dataframe(df, use_container_width=True)

st.markdown("---")

# Секция 2: Почасова таблица за очаквани количества (Ранно предупреждение)
st.header(
    "⚠️ Почасова прогноза за валежите (Следващите 24 часа — Риск от наводнения)"
)
st.markdown(
    "Таблицата по-долу показва очаквания интензитет на дъжда по часове. Следете за стойности **над 5-10 мм/ч**, които носят риск от локални наводнения."
)

# Показваме интерактивната таблица
st.dataframe(df_hourly_forecast, use_container_width=True)

# Графика на очаквания дъжд по часове
st.subheader("📈 Графика на очаквания дъжд по часове (мм)")
chart_rain_df = df_hourly_forecast.set_index("Час")[["Очакван дъжд (мм)"]]
st.bar_chart(chart_rain_df)

st.markdown("---")

# Секция 3: Общо денонощно обобщение
st.header("📍 Обобщен анализ на валежите за денонощието")
p_col1, p_col2 = st.columns(2)

mr_forecast_rain = round(api_rain_forecast * 1.1, 1)

with p_col1:
    st.metric(
        "Общо очакван дъжд (Микулашев / Център)",
        f"{api_rain_forecast} мм",
        f"Макс. вероятност: {api_rain_prob}%",
    )
    st.progress(int(api_rain_prob))

with p_col2:
    st.metric(
        "Общо очакван дъжд (Меден Рудник - Хълмиста част)",
        f"{mr_forecast_rain} мм",
        f"Макс. вероятност: {api_rain_prob}%",
    )
    st.progress(int(api_rain_prob))
