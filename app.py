from __future__ import annotations

import os
import sqlite3
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("METEO_DB_PATH", str(APP_DIR / "meteo_history.sqlite3")))
TZ_NAME = "Europe/Sofia"
TZ = ZoneInfo(TZ_NAME)
API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 15
CACHE_TTL = 900  # 15 min; models may update on their own schedules

LOCATIONS = {
    "Меден Рудник — Бл. 535": {"lat": 42.4785, "lon": 27.4345, "key": "meden_rudnik"},
    "Микулашев — IRUDNI15": {"lat": 42.5048, "lon": 27.4626, "key": "irudni15"},
}

# These model identifiers can change in Open-Meteo. A failed model is reported,
# not replaced with fabricated values.
MODELS = {
    "ECMWF IFS": "ecmwf_ifs025",
    "GFS Seamless": "gfs_seamless",
    "ICON Seamless": "icon_seamless",
}

st.set_page_config(
    page_title="МЕТЕО Дашборд 2.0 | Меден Рудник & IRUDNI15",
    page_icon="🌧️",
    layout="wide",
)
st.title("🌧️ МЕТЕО Дашборд 2.0")
st.caption("Меден Рудник — Бл. 535 · Микулашев — IRUDNI15")
st.info(
    "Прогнозът е ориентировъчен и не замества официалните предупреждения на НИМХ. "
    "При липсващи данни приложението показва грешка, а не измислена прогноза."
)


def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(""" CREATE TABLE IF NOT EXISTS forecast_archive ( id INTEGER PRIMARY KEY AUTOINCREMENT, fetched_at TEXT NOT NULL, location_key TEXT NOT NULL, model TEXT NOT NULL, valid_time TEXT NOT NULL, precipitation_mm REAL, precipitation_probability REAL, temperature_c REAL ) """)
    conn.execute(""" CREATE TABLE IF NOT EXISTS observations ( id INTEGER PRIMARY KEY AUTOINCREMENT, observed_at TEXT NOT NULL, location_key TEXT NOT NULL, precipitation_mm REAL NOT NULL, source TEXT DEFAULT 'manual/CSV' ) """)
    conn.commit()
    return conn


def parse_local_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def clean_hourly_payload(payload: dict, model_label: str) -> pd.DataFrame:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not hourly.get("time"):
        raise ValueError("API отговорът няма почасови данни.")
    required = ["precipitation", "precipitation_probability", "temperature_2m"]
    missing = [name for name in required if name not in hourly]
    if missing:
        raise ValueError("Липсват полета: " + ", ".join(missing))

    lengths = [len(hourly["time"])] + [len(hourly[k]) for k in required]
    if len(set(lengths)) != 1:
        raise ValueError("Несъответстваща дължина на почасовите данни.")

    frame = pd.DataFrame({
        "Време": [parse_local_time(t) for t in hourly["time"]],
        "Валеж (мм)": pd.to_numeric(hourly["precipitation"], errors="coerce"),
        "Вероятност (%)": pd.to_numeric(hourly["precipitation_probability"], errors="coerce"),
        "Температура (°C)": pd.to_numeric(hourly["temperature_2m"], errors="coerce"),
        "Модел": model_label,
    })
    frame = frame.dropna(subset=["Време", "Валеж (мм)", "Температура (°C)"])
    frame["Валеж (мм)"] = frame["Валеж (мм)"].clip(lower=0)
    frame["Вероятност (%)"] = frame["Вероятност (%)"].clip(lower=0, upper=100)
    return frame


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_model_forecast(lat: float, lon: float, model_label: str, model_id: str):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,precipitation",
        "timezone": TZ_NAME,
        "forecast_days": 3,
        "models": model_id,
    }
    response = requests.get(API_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    return clean_hourly_payload(payload, model_label)


def get_all_forecasts(location: dict):
    successes, errors = {}, {}
    for label, model_id in MODELS.items():
        try:
            successes[label] = fetch_model_forecast(
                location["lat"], location["lon"], label, model_id
            )
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            errors[label] = f"{type(exc).__name__}: {exc}"
    return successes, errors


def make_consensus(model_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not model_frames:
        return pd.DataFrame()
    merged = pd.concat(model_frames.values(), ignore_index=True)
    now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0)
    end = now + timedelta(hours=24)
    merged = merged[(merged["Време"] >= now) & (merged["Време"] < end)].copy()
    if merged.empty:
        return merged

    # Equal-weight median is deliberately transparent. It is not a calibrated
    # probability and does not imply the models are statistically independent.
    grouped = merged.groupby("Време", as_index=False).agg(
        **{
            "Очакван валеж (мм)": ("Валеж (мм)", "median"),
            "Средна вероятност (%)": ("Вероятност (%)", "median"),
            "Температура (°C)": ("Температура (°C)", "median"),
            "Разлика между моделите (мм)": ("Валеж (мм)", lambda x: float(x.max() - x.min())),
            "Брой налични модели": ("Модел", "nunique"),
        }
    )
    grouped["Натрупване 3ч (мм)"] = grouped["Очакван валеж (мм)"].rolling(3, min_periods=3).sum()
    grouped["Натрупване 6ч (мм)"] = grouped["Очакван валеж (мм)"].rolling(6, min_periods=6).sum()
    grouped["Натрупване 24ч (мм)"] = grouped["Очакван валеж (мм)"].rolling(24, min_periods=1).sum()
    return grouped


def archive_forecasts(location_key: str, frames: dict[str, pd.DataFrame]):
    if not frames:
        return
    fetched_at = datetime.now(TZ).isoformat()
    rows = []
    for model, df in frames.items():
        for _, row in df.iterrows():
            rows.append((
                fetched_at, location_key, model, row["Време"].isoformat(),
                None if pd.isna(row["Валеж (мм)"]) else float(row["Валеж (мм)"]),
                None if pd.isna(row["Вероятност (%)"]) else float(row["Вероятност (%)"]),
                None if pd.isna(row["Температура (°C)"]) else float(row["Температура (°C)"]),
            ))
    if rows:
        with db_connect() as conn:
            conn.executemany(""" INSERT INTO forecast_archive (fetched_at, location_key, model, valid_time, precipitation_mm, precipitation_probability, temperature_c) VALUES (?, ?, ?, ?, ?, ?, ?) """, rows)


def send_telegram(message: str) -> tuple[bool, str]:
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
    if not token or not chat_id:
        return False, "Telegram не е конфигуриран."
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": str(chat_id), "text": message},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            return False, "Telegram API не потвърди изпращането."
        return True, "Изпратено."
    except (requests.RequestException, ValueError) as exc:
        return False, f"Грешка при Telegram: {exc}"


def alert_level(df: pd.DataFrame) -> tuple[str, str]:
    if df.empty:
        return "НЯМА ДАННИ", "Не може да се определи риск — липсва прогноза."
    max_hour = float(df["Очакван валеж (мм)"].max())
    max_3h = float(df["Натрупване 3ч (мм)"].max()) if df["Натрупване 3ч (мм)"].notna().any() else 0
    max_6h = float(df["Натрупване 6ч (мм)"].max()) if df["Натрупване 6ч (мм)"].notna().any() else 0
    # App-specific screening thresholds, not official warning thresholds.
    if max_hour >= 20 or max_3h >= 35:
        return "ВИСОКО ВНИМАНИЕ", f"Макс. час: {max_hour:.1f} мм; макс. 3ч: {max_3h:.1f} мм."
    if max_hour >= 10 or max_3h >= 20 or max_6h >= 30:
        return "ПОВИШЕНО ВНИМАНИЕ", f"Макс. час: {max_hour:.1f} мм; макс. 3ч: {max_3h:.1f} мм; макс. 6ч: {max_6h:.1f} мм."
    if max_hour >= 0.2:
        return "ВЪЗМОЖЕН ВАЛЕЖ", f"Макс. час: {max_hour:.1f} мм."
    return "НИСКЪК ПРОГНОЗЕН ВАЛЕЖ", "Моделите не показват значително почасово количество."


def load_observations() -> pd.DataFrame:
    with db_connect() as conn:
        return pd.read_sql_query(
            "SELECT observed_at, location_key, precipitation_mm, source FROM observations ORDER BY observed_at DESC",
            conn,
        )


def save_observations(df: pd.DataFrame, source: str):
    needed = {"observed_at", "location_key", "precipitation_mm"}
    if not needed.issubset(df.columns):
        raise ValueError("CSV трябва да съдържа observed_at, location_key, precipitation_mm.")
    rows = []
    for _, row in df.iterrows():
        key = str(row["location_key"]).strip()
        if key not in {v["key"] for v in LOCATIONS.values()}:
            continue
        amount = float(row["precipitation_mm"])
        if amount < 0:
            continue
        rows.append((parse_local_time(str(row["observed_at"])).isoformat(), key, amount, source))
    if not rows:
        raise ValueError("Не са намерени валидни редове за двете локации.")
    with db_connect() as conn:
        conn.executemany(
            "INSERT INTO observations (observed_at, location_key, precipitation_mm, source) VALUES (?, ?, ?, ?)",
            rows,
        )


def validation_summary(location_key: str):
    with db_connect() as conn:
        forecasts = pd.read_sql_query(""" SELECT location_key, model, valid_time, precipitation_mm, fetched_at FROM forecast_archive WHERE location_key = ? """, conn, params=(location_key,))
        obs = pd.read_sql_query(""" SELECT location_key, observed_at, precipitation_mm FROM observations WHERE location_key = ? """, conn, params=(location_key,))
    if forecasts.empty or obs.empty:
        return pd.DataFrame(), "Нужни са архивирани прогнози и реални измервания, за да се оцени точността."
    forecasts["valid_time"] = pd.to_datetime(forecasts["valid_time"], utc=True).dt.floor("h")
    forecasts["fetched_at"] = pd.to_datetime(forecasts["fetched_at"], utc=True)
    obs["observed_at"] = pd.to_datetime(obs["observed_at"], utc=True).dt.floor("h")
    # For each valid hour and model, compare the latest forecast made before that hour.
    forecasts = forecasts[forecasts["fetched_at"] < forecasts["valid_time"]]
    forecasts = forecasts.sort_values("fetched_at").drop_duplicates(
        ["model", "valid_time"], keep="last"
    )
    joined = forecasts.merge(
        obs, left_on=["location_key", "valid_time"], right_on=["location_key", "observed_at"],
        suffixes=("_forecast", "_observed")
    ).dropna(subset=["precipitation_mm_forecast", "precipitation_mm_observed"])
    if joined.empty:
        return pd.DataFrame(), "Все още няма съвпадащи часове прогноза/наблюдение."
    rows = []
    for model, part in joined.groupby("model"):
        error = part["precipitation_mm_forecast"] - part["precipitation_mm_observed"]
        rows.append({
            "Модел": model,
            "Съвпадащи часове": len(part),
            "MAE (мм)": round(float(error.abs().mean()), 3),
            "RMSE (мм)": round(float((error.pow(2).mean()) ** 0.5), 3),
            "Средна грешка (мм)": round(float(error.mean()), 3),
        })
    return pd.DataFrame(rows).sort_values("MAE (мм)"), f"Оценени са {len(joined)} съвпадащи модел-часа."


# Sidebar controls
st.sidebar.header("Настройки")
auto_refresh = st.sidebar.checkbox("Обновяване при отваряне", value=True)
show_models = st.sidebar.checkbox("Покажи отделните модели", value=True)
st.sidebar.caption("Кеш: 15 минути. За нова заявка използвай бутона по-долу.")
if st.sidebar.button("🔄 Изчисти кеша и обнови"):
    st.cache_data.clear()
    st.rerun()

tabs = st.tabs(["Прогноза 24 ч.", "Станционни измервания", "Проверка на точността", "Настройки и помощ"])

with tabs[0]:
    for location_name, location in LOCATIONS.items():
        st.header(location_name)
        with st.spinner(f"Зареждане на моделите за {location_name}..."):
            model_frames, model_errors = get_all_forecasts(location)
        if model_frames:
            archive_forecasts(location["key"], model_frames)
            consensus = make_consensus(model_frames)
            if consensus.empty:
                st.error("Моделите не върнаха достатъчно бъдещи часове за 24-часова прогноза.")
                continue

            level, details = alert_level(consensus)
            if level == "ВИСОКО ВНИМАНИЕ":
                st.error(f"🚨 {level}: {details}")
            elif level == "ПОВИШЕНО ВНИМАНИЕ":
                st.warning(f"⚠️ {level}: {details}")
            elif level == "ВЪЗМОЖЕН ВАЛЕЖ":
                st.info(f"🌧️ {level}: {details}")
            else:
                st.success(f"ℹ️ {level}: {details}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Консенсус — валеж 24ч", f"{consensus['Очакван валеж (мм)'].sum():.1f} мм")
            c2.metric("Макс. почасово количество", f"{consensus['Очакван валеж (мм)'].max():.1f} мм")
            c3.metric("Макс. вероятност (медиана)", f"{consensus['Средна вероятност (%)'].max():.0f}%")
            c4.metric("Налични модели", f"{len(model_frames)}/{len(MODELS)}")

            chart = alt.Chart(consensus).mark_bar().encode(
                x=alt.X("Време:T", title="Час", axis=alt.Axis(format="%H:%M %d.%m")),
                y=alt.Y("Очакван валеж (мм):Q", title="Консенсусен валеж (мм)"),
                tooltip=[
                    alt.Tooltip("Време:T", title="Време"),
                    alt.Tooltip("Очакван валеж (мм):Q", format=".2f"),
                    alt.Tooltip("Средна вероятност (%):Q", format=".0f"),
                    alt.Tooltip("Разлика между моделите (мм):Q", format=".2f"),
                    alt.Tooltip("Брой налични модели:Q"),
                ],
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

            with st.expander("Таблица на консенсуса"):
                display = consensus.copy()
                display["Време"] = display["Време"].dt.strftime("%d.%m.%Y %H:%M")
                st.dataframe(display, use_container_width=True, hide_index=True)

            if show_models:
                st.subheader("Сравнение на моделите")
                plot_frames = []
                for model_name, frame in model_frames.items():
                    temp = frame.copy()
                    now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0)
                    temp = temp[(temp["Време"] >= now) & (temp["Време"] < now + timedelta(hours=24))]
                    plot_frames.append(temp)
                if plot_frames:
                    model_df = pd.concat(plot_frames, ignore_index=True)
                    model_chart = alt.Chart(model_df).mark_line(point=True).encode(
                        x=alt.X("Време:T", axis=alt.Axis(format="%H:%M %d.%m"), title="Час"),
                        y=alt.Y("Валеж (мм):Q", title="Валеж (мм)"),
                        color=alt.Color("Модел:N", title="Модел"),
                        tooltip=["Модел", alt.Tooltip("Време:T"), "Валеж (мм)", "Вероятност (%)"],
                    ).interactive()
                    st.altair_chart(model_chart, use_container_width=True)

            spread_max = float(consensus["Разлика между моделите (мм)"].max())
            if spread_max >= 5:
                st.warning(
                    f"Голяма разлика между моделите: до {spread_max:.1f} мм за отделен час. "
                    "Това е знак за несигурност, не гаранция за точност."
                )
            else:
                st.caption(f"Максимална почасова разлика между наличните модели: {spread_max:.1f} мм.")

            # Explicit user action prevents repeated Telegram messages on every rerun.
            if st.button(f"📨 Изпрати текущото обобщение в Telegram — {location_name}", key=f"tg_{location['key']}"):
                message = (
                    f"МЕТЕО — {location_name}\n"
                    f"Статус: {level}\n{details}\n"
                    f"Консенсусен валеж за 24ч: {consensus['Очакван валеж (мм)'].sum():.1f} мм\n"
                    f"Макс. почасово: {consensus['Очакван валеж (мм)'].max():.1f} мм\n"
                    f"Налични модели: {', '.join(model_frames.keys())}"
                )
                ok, msg = send_telegram(message)
                (st.success if ok else st.warning)(msg)
        else:
            st.error("Няма достъпна прогноза от нито един модел. Не се показват фиктивни стойности.")
        if model_errors:
            with st.expander(f"Проблеми с модели ({len(model_errors)})"):
                for model, err in model_errors.items():
                    st.write(f"**{model}:** {err}")
        st.divider()

with tabs[1]:
    st.subheader("Импорт на реални измервания")
    st.markdown(
        "Първоначалните стойности в стария код са статични примерни данни. "
        "Тук се добавят действителни измервания от станция или CSV файл."
    )
    st.code(
        "observed_at,location_key,precipitation_mm\n"
        "2026-10-13 14:00,meden_rudnik,0.0\n"
        "2026-10-13 14:00,irudni15,0.2",
        language="csv",
    )
    upload = st.file_uploader("Качи CSV с измервания", type=["csv"])
    if upload is not None and st.button("Импортирай измервания"):
        try:
            uploaded_df = pd.read_csv(upload)
            save_observations(uploaded_df, upload.name)
            st.success("Измерванията са добавени в локалната база.")
        except Exception as exc:
            st.error(f"Импортът не успя: {exc}")

    with st.form("manual_observation"):
        st.markdown("**Добави едно измерване ръчно**")
        obs_location = st.selectbox(
            "Локация",
            options=list(LOCATIONS.keys()),
        )
        obs_time = st.datetime_input if False else None
        obs_date = st.date_input("Дата на измерването", value=datetime.now(TZ).date())
        obs_hour = st.selectbox("Час", options=list(range(24)), index=datetime.now(TZ).hour)
        obs_rain = st.number_input("Измерен валеж за този час (мм)", min_value=0.0, max_value=500.0, value=0.0, step=0.1)
        submit_obs = st.form_submit_button("Запази измерването")
    if submit_obs:
        try:
            stamp = datetime(obs_date.year, obs_date.month, obs_date.day, int(obs_hour), tzinfo=TZ)
            with db_connect() as conn:
                conn.execute(
                    "INSERT INTO observations (observed_at, location_key, precipitation_mm, source) VALUES (?, ?, ?, ?)",
                    (stamp.isoformat(), LOCATIONS[obs_location]["key"], float(obs_rain), "manual"),
                )
            st.success("Измерването е записано.")
        except Exception as exc:
            st.error(f"Неуспешен запис: {exc}")

    observations = load_observations()
    if not observations.empty:
        st.dataframe(observations, use_container_width=True, hide_index=True)
        csv_bytes = observations.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Изтегли измерванията като CSV", csv_bytes, "meteo_observations.csv", "text/csv")
    else:
        st.caption("Все още няма реални измервания в локалната база.")

with tabs[2]:
    st.subheader("Историческа проверка на точността")
    st.write(
        "Оценката се изчислява само когато има прогноза, архивирана преди съответния час, "
        "и реално измерване за същия час. При първо стартиране е нормално да няма резултати."
    )
    chosen_location = st.selectbox("Локация за проверка", options=list(LOCATIONS.keys()), key="validation_location")
    metrics_df, message = validation_summary(LOCATIONS[chosen_location]["key"])
    st.info(message)
    if not metrics_df.empty:
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        st.caption("MAE/RMSE по-ниско е по-добре. Средна грешка около 0 означава по-малко систематично надценяване/подценяване.")
    else:
        st.caption("Събирай архив и измервания, за да се появи сравнение. Не се генерират изкуствени оценки.")

with tabs[3]:
    st.subheader("Какво прави версия 2.0")
    st.markdown(""" - Сравнява отделни заявки към ECMWF IFS, GFS Seamless и ICON Seamless. - Изчислява прозрачен медианен консенсус за валежа и вероятността. - Показва разликата между моделите като индикатор за несигурност. - Архивира прогнозните издания в SQLite. - Приема реални часови наблюдения чрез CSV или ръчно въвеждане. - Изчислява MAE и RMSE след натрупване на съвпадащи данни. - Не показва нулева прогноза при API грешка. - Поддържа ръчно Telegram известяване, за да не изпраща повтарящи се съобщения при всяко презареждане. """)
    st.warning(
        "Известията в тази версия се изпращат с бутон. Автоматични фонови известия изискват "
        "постоянно работещ процес/планировчик (например cron, systemd или отделен worker), "
        "защото Streamlit не гарантира изпълнение във фонов режим."
    )
    st.markdown("**Telegram конфигурация**")
    st.code(
        '[secrets]\n'
        'TELEGRAM_BOT_TOKEN = "токен-от-BotFather"\n'
        'TELEGRAM_CHAT_ID = "твоят-chat-id"\n',
        language="toml",
    )
    st.markdown("**CSV формат за наблюдения**")
    st.code(
        "observed_at,location_key,precipitation_mm\n"
        "2026-10-13 14:00,meden_rudnik,0.0\n"
        "2026-10-13 14:00,irudni15,0.2",
        language="csv",
    )
    st.markdown(
        "Валидни `location_key`: `meden_rudnik` и `irudni15`. "
        "Часовете се тълкуват в Europe/Sofia, ако не съдържат часова зона."
    )

st.caption(f"Последно зареждане на интерфейса: {datetime.now(TZ).strftime('%d.%m.%Y %H:%M:%S')} (Europe/Sofia)")
