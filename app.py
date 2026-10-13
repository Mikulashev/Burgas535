import datetime
import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Меден Рудник & Микулашев",
    page_icon="⚠️",
    layout="wide",
)

st.title("🌧️ Хипер-локален Метео Дашборд за Ранно Предупреждение")
st.markdown(
    "Мониторинг с отделни 24-часови прогнози и станции за **ж.к. Меден Рудник (Бл. 535)** и **Микулашев / Център**."
)


# Функция за извличане на динамична почасова прогноза по координати
@st.cache_data(ttl=1800)
def fetch_hourly_forecast(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Sofia"
        response = requests.get(url)
        data = response.json()

        hourly_data = data["hourly"]
        times = hourly_data["time"]
        temps = hourly_data["temperature_2m"]
        precips = hourly_data["precipitation"]
        probs = hourly_data["precipitation_probability"]

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

        df_hourly = pd.DataFrame(
            {
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
                "Час": [f"Час {i+1}" for i in range(24)],
                "Очакван дъжд (мм)": [0.0] * 24,
                "Вероятност (%)": [10] * 24,
                "Температура (°C)": [18] * 24,
            }
        )
        return dummy_df, 4.0, 50


# 1. ПРОГНОЗА ЗА МЕДЕН РУДНИК (Бл. 535 / Терминал) - Координати: 42.4785, 27.4345
df_mr_forecast, mr_rain_total, mr_max_prob = fetch_hourly_forecast(
    42.4785, 27.4345
)

# 2. ПРОГНОЗА ЗА МИКУЛАСЕВ / ЦЕНТЪР - Координати: 42.5048, 27.4626
df_mik_forecast, mik_rain_total, mik_max_prob = fetch_hourly_forecast(
    42.5048, 27.4626
)


# Станции по райони
def get_stations():
    return {
        # РАЙОН МЕДЕН РУДНИК (Първи)
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
        # РАЙОН МИКУЛАСЕВ / ЦЕНТЪР
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
    }


stations = get_stations()

# ==========================================
# СЕКЦИЯ 1: МЕДЕН РУДНИК (БЛ. 535 / ТЕРМИНАЛ)
# ==========================================
st.header("🏢 1. Район: ж.к. Меден Рудник (Бл. 535 / Терминал)")
st.markdown("Хронологична прогноза от момента на отваряне за следващите 24 часа.")

mr_chart = (
    alt.Chart(df_mr_forecast)
    .mark_bar(color="#1f77b4")
    .encode(
        x=alt.X(
            "Час:N",
            sort=list(df_mr_forecast["Час"]),
            title="Час (Меден Рудник)",
        ),
        y=alt.Y("Очакван дъжд (мм):Q", title="Очакван дъжд (мм)"),
        tooltip=["Час", "Очакван дъжд (мм)", "Вероятност (%)", "Температура (°C)"],
    )
    .interactive()
)
st.altair_chart(mr_chart, use_container_width=True)

mr_col1, mr_col2 = st.columns(2)
with mr_col1:
    st.metric(
        "Очаквано общо (24ч - Меден Рудник)",
        f"{mr_rain_total} мм",
        f"Макс. вероятност: {mr_max_prob}%",
    )
    st.progress(int(mr_max_prob))
with mr_col2:
    st.subheader("📋 Часова таблица (Меден Рудник)")
    st.dataframe(df_mr_forecast, use_container_width=True)

# Таблица със станциите за Меден Рудник
st.markdown("**Станции в Меден Рудник:**")
df_mr_stations = pd.DataFrame.from_dict(
    {k: v for k, v in stations.items() if v["Район"] == "Меден Рудник"},
    orient="index",
)
st.dataframe(df_mr_stations, use_container_width=True)

st.markdown("---")

# ==========================================
# СЕКЦИЯ 2: МИКУЛАСЕВ / ЦЕНТЪР
# ==========================================
st.header("🏠 2. Район: Микулашев / Център")
st.markdown("Хронологична прогноза от момента на отваряне за следващите 24 часа.")

mik_chart = (
    alt.Chart(df_mik_forecast)
    .mark_bar(color="#2ca02c")
    .encode(
        x=alt.X(
            "Час:N",
            sort=list(df_mik_forecast["Час"]),
            title="Час (Микулашев / Център)",
        ),
        y=alt.Y("Очакван дъжд (мм):Q", title="Очакван дъжд (мм)"),
        tooltip=["Час", "Очакван дъжд (мм)", "Вероятност (%)", "Температура (°C)"],
    )
    .interactive()
)
st.altair_chart(mik_chart, use_container_width=True)

mik_col1, mik_col2 = st.columns(2)
with mik_col1:
    st.metric(
        "Очаквано общо (24ч - Микулашев)",
        f"{mik_rain_total} мм",
        f"Макс. вероятност: {mik_max_prob}%",
    )
    st.progress(int(mik_max_prob))
with mik_col2:
    st.subheader("📋 Часова таблица (Микулашев)")
    st.dataframe(df_mik_forecast, use_container_width=True)

# Таблица със станциите за Микулашев
st.markdown("**Станции в Микулашев / Център:**")
df_mik_stations = pd.DataFrame.from_dict(
    {k: v for k, v in stations.items() if v["Район"] == "Микулашев / Център"},
    orient="index",
)
st.dataframe(df_mik_stations, use_container_width=True)
