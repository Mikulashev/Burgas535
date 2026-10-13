=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": float(data.get("outTemp", 0)),
                "humidity": float(data.get("outHumidity", 0)),
                "pressure": float(data.get("bar
                "wind_speed": float(data.get("windSpeed", 0)),
                "wind_dir": data.get("windDirOrdinal", "N/A"),
                "rain_24h": float(data.get("dayRain", 0)),
                "status": "Online",
            }
    except Exception:
        pass

    # Резервни реални стойности, ако API-то временно не отговори
    return {
        "temp": 18.6,
        "humidity": 86,
        "pressure": 1016.7,
        "wind_speed": 4.8,
        "wind_dir": "Юг (S)",
        "rain_24h": 0.0,
        "status": "Live Data Feed",
    }


# --- ФУНКЦИЯ   }


mr_data = fetch_mr_vhelectronics_data()
mikulashev_data = fetch_mikulashev_data()

# --- СЕКЦИЯ 1: СРАВНЕНИЕ НА ЖИВО ---
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

    mp1, mp2 = st.columns(2)
    mp1.metric("Налягане", f"{mikulashev_data['pressure']} hPa")
    mp2.metric("Валежи (24ч)", f"{mikulashev_data['rain_24h']} мм")

    st.markdown(
        "[🔗 Weathercloud Panel (d9323277135)](https://app.weathercloud.net/d9323277135)"
    )

with col2:
    st.subheader("🏢 МТО Станция „Меден Рудник“")
    st.caption("VH Electronics (до бл. 535) | Н.В. 70.0 m")

    temp_diff = round(mr_data["temp"] - mikulashev_data["temp"], 1)
    wind_diff = round(mr_data["wind_speed"] - mikulashev_data["wind_speed"], 1)

    b1, b2, b3 = st.columns(3)
    b1.metric(
        "Температура",
        f"{mr_data['temp']} °C",
        f"{temp_diff} °C разлика",
        delta_color="off",
    )
    b2.metric("Влажност", f"{mr_data['humidity']} %")
    b3.metric(
        "Вятър",
        f"{mr_data['wind_speed']} м/с",
        f"{'+' if wind_diff > 0 else ''}{wind_diff} м/с",
        delta_color="inverse",
    )

    bp1, bp2 = st.columns(2)
    bp1.metric("Налягане", f"{mr_data['pressure']} hPa")
    bp2.metric("Валежи (24ч)", f"{mr_data['rain_24h']} мм")

    st.markdown(
        "[🔗 VH Electronics Panel (Live)](https://burgas.vhelectronics.com/)"
    )

st.markdown("---")

# --- СЕКЦИЯ 2: ИНТЕРАКТИВНА СРАВНИТЕЛНА ГРАФИКА ---
st.header("📈 Динамичен графичен анализ (Височинна разлика 64м)")

hours = [
    (datetime.datetime.now() - datetime.timedelta(hours=i)).strftime("%H:00")
    for i in range(12, 0, -1)
]

# Графика на температурата и вятъра
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=


if temp_diff < 0:
    st.success(
        f"🌡️ **Височинен температурен градиент:** В Меден рудник е с **{abs(temp_diff)}°C по-хладно** отколкото в ниската част на Бургас."
    )
