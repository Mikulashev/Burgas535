import datetime
import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="МЕТЕО Дашборд | Меден Рудник & Микулашев (IRUDNI15)",
    page_icon="⚠️",
    layout="wide",
)

# ---- СТРАНИЧНО МЕНЮ: НАСТРОЙКИ И TELEGRAM АЛАРМИ ----
st.sidebar.title("⚙️ Настройки и Известия")
st.sidebar.markdown(
    "Конфигурирайте вашия **Telegram Bot**, за да получавате спешни аларми при интензивни валежи."
)

telegram_token = st.sidebar.text_input("Telegram Bot Token", type="password")
telegram_chat_id = st.sidebar.text_input(
    "Telegram Chat ID",
    help="ID на вашия чат или канал, към който да се изпращат известията.",
)


def send_telegram_alert(message):
    if not telegram_token or not telegram_chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except:
        return False


st.title("🌧️ Хипер-локален Метео Дашборд за Ранно Предупреждение")
st.markdown(
    "Мониторинг с мултимоделен консенсус, акумулирани валежи и проверка на станциите за **ж.к. Меден Рудник (Бл. 535)** и **Микулашев (IRUDNI15)**."
)


# 1. Функция за извличане на почасова прогноза (Open-Meteo / Best Match)
@st.cache_data(ttl=1800)
def fetch_hourly_forecast(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,precipitation&models=best_match&timezone=Europe/Sofia"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
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
        temps_slice = list(temps[start_idx:end_idx])
        precips_slice = list(precips[start_idx:end_idx])
        probs_slice = list(probs[start_idx:end_idx])

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

        df_hourly["Дъжд 3ч (мм)"] = (
            df_hourly["Очакван дъжд (мм)"]
            .rolling(window=3, min_periods=1)
            .sum()
            .round(1)
        )
        df_hourly["Дъжд 6ч (мм)"] = (
            df_hourly["Очакван дъжд (мм)"]
            .rolling(window=6, min_periods=1)
            .sum()
            .round(1)
        )

        total_rain = sum(precips_slice)
        max_prob = max(probs_slice) if probs_slice else 0
        max_hourly_rain = max(precips_slice) if precips_slice else 0.0
        max_3h_rain = (
            df_hourly["Дъжд 3ч (мм)"].max() if not df_hourly.empty else 0.0
        )
        max_6h_rain = (
            df_hourly["Дъжд 6ч (мм)"].max() if not df_hourly.empty else 0.0
        )

        return (
            df_hourly,
            round(total_rain, 1),
            max_prob,
            max_hourly_rain,
            max_3h_rain,
            max_6h_rain,
            None,
        )
    except Exception as e:
        return None, 0.0, 0, 0.0, 0.0, 0.0, str(e)


# 2. Функция за безопасна проверка на станции без показване на измислени данни
def get_station_status(station_name, network_type):
    # Тук гарантираме че при липса на директна интеграция не показваме фалшиви числа, а реален статус
    return {
        "Стация": station_name,
        "Мрежа": network_type,
        "Статус": "⚪ В очакване на директен живи поток",
        "Темп. (°C)": "Н/Д",
        "Влажност (%)": "Н/Д",
        "Дъжд 24ч (мм)": "Н/Д",
    }


# Извличане на прогнози за двете точки
df_mr, mr_total, mr_prob, mr_h1, mr_h3, mr_h6, mr_err = fetch_hourly_forecast(
    42.4785, 27.4345
)
df_mik, mik_total, mik_prob, mik_h1, mik_h3, mik_h6, mik_err = (
    fetch_hourly_forecast(42.5048, 27.4626)
)

# Станции по райони с коректно отчитане
stations_list = [
    {
        "Район": "Меден Рудник",
        "Име": "Меден Рудник - Бл. 535",
        "Код": "VH-535",
        "Мрежа": "Локална",
    },
    {
        "Район": "Меден Рудник",
        "Име": "IBURGA54",
        "Код": "IBURGA54",
        "Мрежа": "Weather Underground",
    },
    {
        "Район": "Меден Рудник",
        "Име": "IBURGA90",
        "Код": "IBURGA90",
        "Мрежа": "Weather Underground",
    },
    {
        "Район": "Микулашев",
        "Име": "Микулашев (IRUDNI15)",
        "Код": "IRUDNI15",
        "Мрежа": "Weather Underground",
    },
    {
        "Район": "Микулашев",
        "Име": "Микулашев (Weathercloud)",
        "Код": "d9323277135",
        "Мрежа": "Weathercloud",
    },
]

# ==========================================
# СЕКЦИЯ 1: МЕДЕН РУДНИК (БЛ. 535)
# ==========================================
st.header("🏢 1. Район: ж.к. Меден Рудник (Бл. 535)")

if mr_err:
    st.error(f"🚨 Грешка при зареждане на прогнозата: {mr_err}")
else:
    if mr_h1 >= 40.0 or mr_h3 >= 60.0:
        msg = f"🚨 *КРИТИЧНО ПРЕДУПРЕЖДЕНИЕ (Меден Рудник)*: Очакват се опасни валежи! Пик 1ч: {mr_h1} мм/ч, 3ч сума: {mr_h3} мм."
        st.error(msg)
        send_telegram_alert(msg)
    elif mr_h1 >= 20.0 or mr_h3 >= 35.0:
        msg = f"⚠️ *ВНИМАНИЕ (Меден Рудник)*: Интензивен валеж! Пик 1ч: {mr_h1} мм/ч, 3ч сума: {mr_h3} мм."
        st.warning(msg)
        send_telegram_alert(msg)
    else:
        st.success(
            "✅ Нормална валежна обстановка в Меден Рудник за следващите 24 часа."
        )

    mr_chart = (
        alt.Chart(df_mr)
        .mark_bar(color="#1f77b4")
        .encode(
            x=alt.X(
                "Час:N", sort=list(df_mr["Час"]), title="Час (Меден Рудник)"
            ),
            y=alt.Y("Очакван дъжд (мм):Q", title="Очакван дъжд (мм)"),
            tooltip=[
                "Час",
                "Очакван дъжд (мм)",
                "Дъжд 3ч (мм)",
                "Вероятност (%)",
                "Температура (°C)",
            ],
        )
        .interactive()
    )
    st.altair_chart(mr_chart, use_container_width=True)

    mr_col1, mr_col2 = st.columns(2)
    with mr_col1:
        st.metric(
            "Очаквано общо (24ч - Меден Рудник)",
            f"{mr_total} мм",
            f"Макс. вероятност: {mr_prob}%",
        )
        st.progress(int(mr_prob))
    with mr_col2:
        st.subheader("📋 Часова таблица и акумулирани валежи")
        st.dataframe(df_mr, use_container_width=True)

    st.markdown("**Станции в Меден Рудник:**")
    df_mr_st = pd.DataFrame(
        [
            get_station_status(s["Име"], s["Мрежа"])
            for s in stations_list
            if s["Район"] == "Меден Рудник"
        ]
    )
    st.dataframe(df_mr_st, use_container_width=True)

st.markdown("---")

# ==========================================
# СЕКЦИЯ 2: МИКУЛАСЕВ (IRUDNI15)
# ==========================================
st.header("🏠 2. Район: Микулашев (Станция IRUDNI15)")

if mik_err:
    st.error(f"🚨 Грешка при зареждане на прогнозата: {mik_err}")
else:
    if mik_h1 >= 40.0 or mik_h3 >= 60.0:
        msg = f"🚨 *КРИТИЧНО ПРЕДУПРЕЖДЕНИЕ (Микулашев)*: Очакват се опасни валежи! Пик 1ч: {mik_h1} мм/ч, 3ч сума: {mik_h3} мм."
        st.error(msg)
        send_telegram_alert(msg)
    elif mik_h1 >= 20.0 or mik_h3 >= 35.0:
        msg = f"⚠️ *ВНИМАНИЕ (Микулашев)*: Интензивен валеж! Пик 1ч: {mik_h1} мм/ч, 3ч сума: {mik_h3} мм."
        st.warning(msg)
        send_telegram_alert(msg)
    else:
        st.success("✅ Нормална валежна обстановка в Микулашев за следващите 24 часа.")

    mik_chart = (
        alt.Chart(df_mik)
        .mark_bar(color="#2ca02c")
        .encode(
            x=alt.X(
                "Час:N", sort=list(df_mik["Час"]), title="Час (Микулашев)"
            ),
            y=alt.Y("Очакван дъжд (мм):Q", title="Очакван дъжд (мм)"),
            tooltip=[
                "Час",
                "Очакван дъжд (мм)",
                "Дъжд 3ч (мм)",
                "Вероятност (%)",
                "Температура (°C)",
            ],
        )
        .interactive()
    )
    st.altair_chart(mik_chart, use_container_width=True)

    mik_col1, mik_col2 = st.columns(2)
    with mik_col1:
        st.metric(
            "Очаквано общо (24ч - Микулашев / IRUDNI15)",
            f"{mik_total} мм",
            f"Макс. вероятност: {mik_prob}%",
        )
        st.progress(int(mik_prob))
    with mik_col2:
        st.subheader("📋 Часова таблица и акумулирани валежи")
        st.dataframe(df_mik, use_container_width=True)

    st.markdown("**Станции в Микулашев (вкл. IRUDNI15):**")
    df_mik_st = pd.DataFrame(
        [
            get_station_status(s["Име"], s["Мрежа"])
            for s in stations_list
            if s["Район"] == "Микулашев"
        ]
    )
    st.dataframe(df_mik_st, use_container_width=True)
