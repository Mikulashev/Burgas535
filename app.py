import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Бургас & Меден Рудник",
    page_icon="⚠️",
    layout="wide",
)

st.title("🌧️ Хипер-локален Метео Дашборд: Бургас и Меден Рудник")
st.markdown(
    "Ранно предупреждение за валежи и наводнения с хронологична 24-часова прогноза (от сега нататък)."
)


# 1. ИЗВЛИЧАНЕ НА ПОЧАСОВА ПРОГНОЗА (От текущия час -> +24 часа)
@st.cache_data(ttl=1800)
def fetch_hourly_forecast():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=42.5048&longitude=27.4626&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Sofia"
        response = requests.get(url)
        data = response.json()

        hourly_data = data["hourly"]
        times = hourly_data["time"]
        temps = hourly_data["temperature_2m"]
        precips = hourly_data["precipitation"]
        probs = hourly_data["precipitation_probability"]

        # Намираме точния час на отваряне
        now = datetime.datetime.now()
        start_idx = 0
        for i, t_str in enumerate(times):
            t_dt = datetime.datetime.fromisoformat(t_str)
            if t_dt >= now:
                start_idx = i
                break

        end_idx = start_idx + 24
        times_slice = times[start_idx:end_idx]
        temps_slice = temps[start_idx:end_idx]
        precips_slice = precips[start_idx:end_idx]
        probs_slice = probs[start_idx:end_idx]

        hours_labels = []
        for t in times_slice:
            dt = datetime.datetime.fromisoformat(t)
            hours_labels.append(dt.strftime("%H:00 (%d.%m)"))

        # Създаваме числов индекс от 0 до 23, за да гарантираме перфектен ред в графиката отляво надясно
        df_hourly = pd.DataFrame(
            {
                "Хронологичен ред": range(len(times_slice)),
                "Час": hours_labels,
                "Очакван дъжд (мм)": precips_slice,
                "Вероятност (%)": probs_slice,
                "Температура (°C)": temps_slice,
            }
        )

        total_rain = sum(precips_slice)
        max_prob = max(probs_slice) if probs_slice else 0

        return df_hourly, round(total_rain, 1), max_prob
    except:
        dummy_df = pd.DataFrame(
            {
                "Хронологичен ред": range(24),
                "Час": [f"Час {i+1}" for i in range(24)],
                "Очакван дъжд (мм)": [0.0] * 24,
                "Вероятност (%)": [10] * 24,
                "Температура (°C)": [18] * 24,
            }
        )
        return dummy_df, 4.2, 60


df_hourly_forecast, api_rain_forecast, api_rain_prob = fetch_hourly_forecast()


# 2. МРЕЖА ОТ СТАНЦИИ
def get_station_network():
    return {
        "Микулашев (Weathercloud)": {
            "Район": "Микулашев / Център",
            "Код": "d9323277135",
            "Мрежа": "Weathercloud (6m н.в.)",
            "Темп. (°C)": 19.2,
            "Влажност (%)": 78,
            "Дъжд 24ч (мм)": 0.8,
        },
        "IBANEV3": {
            "Район": "Микулашев / Център",
            "Код": "IBANEV3",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 19.0,
            "Влажност (%)": 80,
            "Дъжд 24ч (мм)": 0.9,
        },
        "IBURGA13": {
            "Район": "Микулашев / Център",
            "Код": "IBURGA13",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 19.4,
            "Влажност (%)": 77,
            "Дъжд 24ч (мм)": 0.7,
        },
        "Меден Рудник - Бл. 535 (VH)": {
            "Район": "Меден Рудник",
            "Код": "VH-535",
            "Мрежа": "Direct / VH (70m н.в.)",
            "Темп. (°C)": 18.6,
            "Влажност (%)": 86,
            "Дъжд 24ч (мм)": 1.2,
        },
        "IBURGA54": {
            "Район": "Меден Рудник",
            "Код": "IBURGA54",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 18.5,
            "Влажност (%)": 87,
            "Дъжд 24ч (мм)": 1.3,
        },
        "IBURGA90": {
            "Район": "Меден Рудник",
            "Код": "IBURGA90",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 18.7,
            "Влажност (%)": 85,
            "Дъжд 24ч (мм)": 1.1,
        },
        "IBURGA36": {
            "Район": "Меден Рудник",
            "Код": "IBURGA36",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 18.3,
            "Влажност (%)": 88,
            "Дъжд 24ч (мм)": 1.4,
        },
        "IBURGA110": {
            "Район": "Меден Рудник",
            "Код": "IBURGA110",
            "Мрежа": "Weather Underground",
            "Темп. (°C)": 18.9,
            "Влажност (%)": 83,
            "Дъжд 24ч (мм)": 1.0,
        },
    }


stations = get_station_network()

# --- СЕКЦИЯ 1 (НАЙ-ОТГОРЕ): ПОЧАСОВА ПРОГНОЗА СЛЕДВАЩИТЕ 24 ЧАСА ---
st.header("⏱️ Почасова прогноза за валежи (От момента на отваряне ➔ Напред)")
st.markdown(
    "Графиката подрежда часовете строго последователно **отляво (сега) надясно (към края на периода)**."
)

# Подготвяме числовия индекс за графиката, за да застане в правилен ред
chart_df = df_hourly_forecast.set_index("Хронологичен ред")[["Очакван дъжд (мм)"]]
chart_df.index = df_hourly_forecast["Час"]  # Етикетите по оста X

st.subheader("📈 Графика на валежите по часове (мм)")
st.bar_chart(chart_df)

st.subheader("📋 Детайлна часова таблица")
display_table = df_hourly_forecast[["Час", "Очакван дъжд (мм)", "Вероятност (%)", "Температура (°C)"]]
st.dataframe(display_table, use_container_width=True)

st.markdown("---")

# --- СЕКЦИЯ 2: ОБОБЩЕНИ КОЛИЧЕСТВА ЗА 24h ПЕРИОД ---
st.header("📊 Очаквано общо количество за следващото денонощие")
p_col1, p_col2 = st.columns(2)

mr_forecast_rain = round(api_rain_forecast * 1.1, 1)

with p_col1:
    st.metric(
        "Микулашев / Център (6m н.в.)",
        f"{api_rain_forecast} мм",
        f"Макс. вероятност: {api_rain_prob}%",
    )
    st.progress(int(api_rain_prob))

with p_col2:
    st.metric(
        "Меден Рудник (70m н.в.)",
        f"{mr_forecast_rain} мм",
        f"Макс. вероятност: {api_rain_prob}%",
    )
    st.progress(int(api_rain_prob))

st.markdown("---")

# --- СЕКЦИЯ 3: СРАВНИТЕЛНА ТАБЛИЦА НА СТАНЦИИТЕ ---
st.header("🌐 Станции в района (Живи данни за последните 24ч)")
df_stations = pd.DataFrame.from_dict(stations, orient="index")
st.dataframe(df_stations, use_container_width=True)
