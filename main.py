import streamlit as st
from stravalib.client import Client
import pandas as pd
import plotly.express as px
import json
import os
import time
import requests

# ==========================================
# ⚙️ KONFIGURACJA I SETUP
# ==========================================

st.set_page_config(
    page_title="CoachPlus Dashboard",
    page_icon="intmon.png",
    layout="wide"
)

# Ładowanie sekretów
try:
    MY_CLIENT_ID = st.secrets["MY_CLIENT_ID"]
    MY_CLIENT_SECRET = st.secrets["MY_CLIENT_SECRET"]
except FileNotFoundError:
    st.error("Brak skonfigurowanych sekretów! (folder .streamlit/secrets.toml)")

# --- WYCISZENIE OSTRZEŻEŃ STRAVALIB ---
os.environ["SILENCE_TOKEN_WARNINGS"] = "true"

# Plik bazy danych
DB_FILE = 'zawodnicy.json'

# Logo aplikacji
st.logo(
    "intmon.png",
    icon_image="intmon.png",
)

# ==========================================
# 🚦 ROUTER (STEROWANIE STRONAMI)
# ==========================================

query_params = st.query_params

# --- SCENARIUSZ A: POLITYKA PRYWATNOŚCI ---
if query_params.get("strona") == "prywatnosc":

    # Przycisk powrotu
    if st.button("Wróć do aplikacji"):
        st.query_params.clear() # Czyści link z "?strona=prywatnosc"
        st.rerun()              # Odświeża stronę do stanu początkowego

    st.markdown("""
    # Privacy Policy
    **Effective Date:** February 11, 2026

    This Privacy Policy describes how the **Coaching Dashboard** ("we", "us", or "our") collects, uses, and shares your personal data when you use our application powered by the Strava API.

    ## 1. Introduction
    This application is an internal tool designed specifically for coaching purposes. Its primary goal is to visualize training data to help athletes and coaches analyze performance and adjust training plans.

    ## 2. Data We Collect
    We do not collect any data without your explicit consent. When you authorize our application via Strava, we access the following information through the Strava API:
    * **Profile Information:** First name, last name.
    * **Activity Data:** Activity type (run, ride, swim, etc.), distance, duration, speed/pace, heart rate, and dates of activities.

    ## 3. How We Use Your Data
    The data collected is used strictly for the following purposes:
    * To display training statistics and charts within the application dashboard.
    * To allow an authorized coach to monitor training loads and progress.

    We **do not** use your data for advertising, marketing, or any commercial purposes unrelated to the coaching service.

    ## 4. Data Sharing and Storage
    **We do not sell your personal data.**

    The data is processed in real-time or cached temporarily to improve application performance. We do not share your Strava data with any third parties, except as required by law.

    ## 5. Your Rights and Control
    You have full control over your data:
    * **Revoke Access:** You can disconnect this application at any time by going to your [Strava Settings > My Apps](https://www.strava.com/settings/apps) and clicking "Revoke Access".
    * **Data Deletion:** Upon revocation, the application will no longer have access to your Strava account.

    ## 6. Contact Us
    If you have any questions about this Privacy Policy, please contact the developer:

    **Email:** intmondev@gmail.com

    ---
    *This application is powered by the Strava API but is not endorsed or certified by Strava.*
    """)
    st.stop()

# --- SCENARIUSZ B: SUKCES PO AUTORYZACJI ---
if query_params.get("strona") == "sukces":

    # Przycisk powrotu
    if st.button("Wróć do aplikacji"):
        st.query_params.clear() # Czyści link z "?strona=sukces"
        st.rerun()              # Odświeża stronę do stanu początkowego

    auth_code = query_params.get("code", ["Błąd"])[0] if isinstance(query_params.get("code"), list) else query_params.get("code")
    
    st.balloons()
    st.success("✅ Konto Strava połączone pomyślnie!")
    
    st.markdown(f"""
    ### Co teraz?
    Skopiuj poniższy kod i wyślij go swojemu trenerowi:
    """)
    st.code(auth_code, language="text")
    st.info("Możesz już zamknąć to okno.")
    st.stop()

# ==========================================
# 🛠️ FUNKCJE POMOCNICZE
# ==========================================

def render_footer():
    """Wyświetla stopkę na dole strony"""
    LINK_DO_POLITYKI = "https://td-analysis.streamlit.app/?strona=prywatnosc"

    st.markdown(f"""
        <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #0e1117;
            color: #FAFAFA;
            text-align: center;
            padding: 10px;
            border-top: 1px solid #333;
            z-index: 9999;
            font-size: 13px;
        }}
        .footer a {{
            color: #FC4C02;
            text-decoration: none;
            font-weight: bold;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        .block-container {{
            padding-bottom: 60px; 
        }}
        </style>
        
        <div class="footer">
            <p style="margin: 0;">
                © 2026 <b>IntMonDev</b>. All rights reserved. 
                | Created using Strava API 
                | <a href="{LINK_DO_POLITYKI}" target="_blank">Polityka Prywatności</a>
            </p>
        </div>
        """, unsafe_allow_html=True)

def check_password():
    """Obsługa logowania hasłem głównym"""
    if "APP_PASSWORD" not in st.secrets:
        st.error("Nie skonfigurowano hasła w secrets.toml!")
        return False

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown("## Dashboard - Logowanie")
    password = st.text_input("Podaj hasło dostępu", type="password")
    
    if st.button("Zaloguj"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Błędne hasło")
            
    return False

def load_db():
    """Wczytuje bazę. Jeśli pusta/brak pliku, ładuje Master Usera z sekretów."""
    db = {}
    
    # 1. Próba wczytania z pliku (jeśli istnieje)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                db = json.load(f)
        except:
            pass # Jeśli błąd pliku, ignorujemy i lecimy dalej

    # 2. Sprawdzenie czy mamy Master Usera w sekretach (Fallback)
    # Jeśli baza jest pusta LUB nie ma w niej Trenera, a mamy go w sekretach -> dodajemy go
    if "master_user" in st.secrets:
        master = st.secrets["master_user"]
        master_name = master["name"]
        
        if master_name not in db:
            db[master_name] = {
                'access_token': master["access_token"],
                'refresh_token': master["refresh_token"],
                'expires_at': master["expires_at"]
            }
            # Opcjonalnie: zapisujemy to od razu do pliku, żeby działało w tej sesji
            try:
                with open(DB_FILE, 'w') as f:
                    json.dump(db, f, indent=4)
            except:
                pass

    return db

def save_db(db):
    # 1. Zapis lokalny (wymagany do działania obecnej sesji Streamlita)
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)
        
    # 2. Automatyczny backup na Discorda
    # 2. Automatyczny backup na Discorda
    if "DISCORD_WEBHOOK" in st.secrets:
        try:
            with open(DB_FILE, 'rb') as f:
                payload = {"content": "🔄 **Backup bazy zawodników!**"}
                files = {"file": ("zawodnicy.json", f, "application/json")}
                requests.post(st.secrets["DISCORD_WEBHOOK"], data=payload, files=files)
        except Exception as e:
            # ZMIENIONE: Zamiast 'pass', wymuszamy pokazanie błędu na ekranie
            import streamlit as st
            st.error(f"Błąd Discorda: {e}")

def extract_number(value, type_hint="number"):
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    
    if type_hint == "time":
        if hasattr(value, 'total_seconds'): return value.total_seconds()
        if hasattr(value, 'seconds'): return value.seconds
        
    if hasattr(value, 'magnitude'): return float(value.magnitude)
    if hasattr(value, 'num'): return float(value.num)
    
    try: return float(value)
    except: return 0.0

# ==========================================
# 🔐 URUCHOMIENIE LOGOWANIA I STOPKI
# ==========================================

render_footer()

if not check_password():
    st.stop()

# ==========================================
# 📱 GŁÓWNY INTERFEJS APLIKACJI
# ==========================================

st.title("Panel Trenera")

tab1, tab2 = st.tabs(["Analiza Treningów", "Dodaj Zawodnika (Ręcznie)"])

# --- ZAKŁADKA 1: ANALIZA ---
with tab1:
    db = load_db()
    
    if not db:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby kogoś dodać.")
    else:
        imiona = list(db.keys())
        wybrany_imie = st.selectbox("Wybierz podopiecznego:", imiona)
        
        if wybrany_imie:
            zawodnik_data = db[wybrany_imie]
            client = Client()
            
            # Automatyczne odświeżanie tokena
            if time.time() > zawodnik_data['expires_at']:
                try:
                    refresh_response = client.refresh_access_token(
                        client_id=MY_CLIENT_ID,
                        client_secret=MY_CLIENT_SECRET,
                        refresh_token=zawodnik_data['refresh_token']
                    )
                    db[wybrany_imie]['access_token'] = refresh_response['access_token']
                    db[wybrany_imie]['refresh_token'] = refresh_response['refresh_token']
                    db[wybrany_imie]['expires_at'] = refresh_response['expires_at']
                    save_db(db)
                except Exception as e:
                    st.error(f"Nie udało się odświeżyć tokena: {e}")

            client.access_token = db[wybrany_imie]['access_token']
            
            # --- FILTRY ---
            st.write("---")
            st.subheader("Ustawienia analizy")
            
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Filtruj od dnia", value=pd.to_datetime("today") - pd.Timedelta(days=7))
            end_date = col2.date_input("Filtruj do dnia", value=pd.to_datetime("today") + pd.Timedelta(days=1))

            TYPE_MAP = {
                "Run": "Bieganie", "VirtualRun": "Bieganie", "TrailRun": "Bieganie",
                "Ride": "Jazda na rowerze", "VirtualRide": "Jazda na rowerze", "EBikeRide": "Jazda na rowerze",
                "GravelRide": "Jazda na rowerze", "MountainBikeRide": "Jazda na rowerze",
                "Swim": "Pływanie", "Walk": "Spacer", "Hike": "Wędrówka",
                "WeightTraining": "Siłownia", "Workout": "Trening", "Yoga": "Joga",
                "Rowing": "Wiosłowanie", "VirtualRow": "Wiosłowanie",
                "NordicSki": "Bieganie na nartach", "BackcountrySki": "Bieganie na nartach", "RollerSki": "Bieganie na nartach"
            }
            
            # --- CHECKBOXY ZAMIAST MULTISELECTA ---
            st.markdown("**Wybierz typy aktywności do analizy:**")
            
            # Tworzymy 3 kolumny
            c1, c2, c3 = st.columns(3)
            
            wybrane_typy = []
            
            # Rząd 1
            if c1.checkbox("Bieganie", value=False): 
                wybrane_typy.append("Bieganie")
            if c2.checkbox("Jazda na rowerze", value=False): 
                wybrane_typy.append("Jazda na rowerze")
            if c3.checkbox("Pływanie", value=False): 
                wybrane_typy.append("Pływanie")
                
            # Rząd 2
            if c1.checkbox("Bieganie na nartach", value=False): 
                wybrane_typy.append("Bieganie na nartach")
            if c2.checkbox("Wiosłowanie", value=False): 
                wybrane_typy.append("Wiosłowanie")
            if c3.checkbox("Siłownia", value=False): 
                wybrane_typy.append("Siłownia")
                
            # Rząd 3
            if c1.checkbox("Spacer", value=False): 
                wybrane_typy.append("Spacer")
            if c2.checkbox("Inne", value=False): 
                wybrane_typy.append("Inne")

            if st.button("Pobierz i filtruj treningi"):
                with st.spinner('Pobieram i przetwarzam dane...'):
                    try:
                        activities = client.get_activities(after=str(start_date), before=str(end_date), limit=100)
                        
                        data = []
                        nierozpoznane_typy = set()
                        
                        # Dodajemy słownik na strefy tętna (czasy w sekundach)
                        hr_zones_aggregated = {
                            "Z1 (Regeneracja)": 0,
                            "Z2 (Wytrzymałość)": 0,
                            "Z3 (Tempo)": 0,
                            "Z4 (Próg)": 0,
                            "Z5 (Anaerobowa)": 0
                        }

                        for activity in activities:
                            # 1. POBIERANIE TYPU
                            raw_type = getattr(activity, 'sport_type', None)
                            if not raw_type:
                                raw_type = activity.type
                            
                            raw_type_str = str(raw_type)\
                                .replace("root='", "")\
                                .replace("'", "")\
                                .replace("ActivityType.", "")
                            
                            polski_typ = TYPE_MAP.get(raw_type_str, "Inne")
                            
                            if polski_typ == "Inne":
                                nierozpoznane_typy.add(raw_type_str)

                            # 2. PRZELICZANIE
                            dist_km = round(extract_number(activity.distance) / 1000, 2)
                            duration_min = round(extract_number(activity.moving_time, "time") / 60, 2)
                            avg_hr = round(extract_number(activity.average_heartrate))
                            
                            # Tempo
                            avg_speed_ms = extract_number(activity.average_speed)
                            pace_str = "-"
                            if avg_speed_ms > 0:
                                # Zmiana tutaj: sprawdzamy czy to Bieganie LUB Bieganie na nartach
                                if polski_typ in ["Bieganie", "Bieganie na nartach"]:
                                    pace_decimal = (1000 / avg_speed_ms) / 60
                                    p_min = int(pace_decimal)
                                    p_sec = int((pace_decimal - p_min) * 60)
                                    pace_str = f"{p_min}:{p_sec:02d} /km"
                                elif polski_typ == "Jazda na rowerze":
                                    speed_kmh = round(avg_speed_ms * 3.6, 1)
                                    pace_str = f"{speed_kmh} km/h"
                                elif polski_typ == "Pływanie":
                                    pace_decimal = (100 / avg_speed_ms) / 60
                                    p_min = int(pace_decimal)
                                    p_sec = int((pace_decimal - p_min) * 60)
                                    pace_str = f"{p_min}:{p_sec:02d} /100m"
                                # Opcjonalnie: wiosłowanie zazwyczaj podaje się na 500m, 
                                # ale na razie zostawiamy bazowe ustawienia dla reszty.

                            activity_url = f"https://www.strava.com/activities/{activity.id}"
                            
                            data.append({
                                "Data": activity.start_date_local.strftime("%Y-%m-%d"),
                                "Typ Polski": polski_typ,
                                "Typ": raw_type_str,
                                "Nazwa": activity.name,
                                "Dystans (km)": dist_km,
                                "Czas (min)": duration_min,
                                "Tętno": avg_hr,
                                "Tempo": pace_str,
                                "Link": activity_url
                            })
                            # --- POBIERANIE STREF TĘTNA ---
                            # Pobieramy zawsze, jeśli trening w ogóle ma zapisane tętno
                            if getattr(activity, 'has_heartrate', False):
                                try:
                                    zones = client.get_activity_zones(activity.id)
                                    for z in zones:
                                        if z.type == 'heartrate' and getattr(z, 'distribution_buckets', None):
                                            buckets = z.distribution_buckets
                                            if len(buckets) >= 5:
                                                hr_zones_aggregated["Z1 (Regeneracja)"] += buckets[0].time
                                                hr_zones_aggregated["Z2 (Wytrzymałość)"] += buckets[1].time
                                                hr_zones_aggregated["Z3 (Tempo)"] += buckets[2].time
                                                hr_zones_aggregated["Z4 (Próg)"] += buckets[3].time
                                                hr_zones_aggregated["Z5 (Anaerobowa)"] += buckets[4].time
                                except Exception as e:
                                    pass # Ignorujemy błędy (np. brak premium odrzuci to zapytanie)
                        
                        # --- DIAGNOSTYKA I WYNIKI ---
                        if nierozpoznane_typy:
                            st.warning(f"⚠️ Znaleziono nowe typy: {nierozpoznane_typy}")

                        if data:
                            df = pd.DataFrame(data)
                            df_filtered = df[df["Typ Polski"].isin(wybrane_typy)]
                            
                            if df_filtered.empty:
                                st.warning(f"Brak treningów pasujących do filtra: {wybrane_typy}")
                            else:
                                df_filtered['Nazwa Treningu'] = df_filtered.apply(
                                    lambda x: f'<a href="{x["Link"]}" target="_blank" style="text-decoration:none; color:#FC4C02; font-weight:bold;">{x["Nazwa"]}</a>', 
                                    axis=1
                                )

                                final_df = df_filtered[[
                                    'Data', 'Typ', 'Nazwa Treningu', 
                                    'Dystans (km)', 'Czas (min)', 'Tętno', 'Tempo'
                                ]]
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Liczba treningów", len(final_df))
                                c2.metric("Suma km", round(final_df['Dystans (km)'].sum(), 1))
                                c3.metric("Czas (h)", round(final_df['Czas (min)'].sum() / 60, 1))

                                st.write("---")
                                st.markdown(
                                    final_df.to_html(escape=False, index=False), 
                                    unsafe_allow_html=True
                                )
                                
                                # --- WYKRES DYSTANSU ---
                                if "Dystans (km)" in final_df.columns and final_df["Dystans (km)"].sum() > 0:
                                    
                                    # INTELIGENTNE KOLOROWANIE:
                                    if len(wybrane_typy) > 1:
                                        kolor_wg = "Typ" 
                                        tytul_wykresu = "Dzienny dystans"
                                    else:
                                        # Skoro na osi Y jest dystans, pokolorujmy słupki na podstawie intensywności (Tętna)
                                        kolor_wg = "Tętno" 
                                        tytul_wykresu = f"Dzienny dystans ({wybrane_typy[0]})"

                                    fig = px.bar(
                                        final_df, 
                                        x="Data", 
                                        y="Dystans (km)", 
                                        title=tytul_wykresu, 
                                        color=kolor_wg,
                                        hover_data=["Nazwa Treningu", "Czas (min)", "Tempo", "Tętno"] 
                                    )
                                    st.plotly_chart(fig)
                                
                                # ==========================================
                                # WIZUALIZACJA STREF TĘTNA
                                # ==========================================
                                st.write("---")
                                st.subheader("Analiza stref tętna")

                                if sum(hr_zones_aggregated.values()) > 0:
                                    # Mamy dane -> Rysujemy wykresy
                                    df_zones = pd.DataFrame({
                                        "Strefa": list(hr_zones_aggregated.keys()),
                                        "Czas (min)": [round(v / 60, 1) for v in hr_zones_aggregated.values()]
                                    })
                                    
                                    # Sztywne przypisanie kolorów do stref (najbezpieczniejsza metoda)
                                    kolory_stref = {
                                        "Z1 (Regeneracja)": "#9E9E9E",
                                        "Z2 (Wytrzymałość)": "#2196F3",
                                        "Z3 (Tempo)": "#4CAF50",
                                        "Z4 (Próg)": "#FF9800",
                                        "Z5 (Anaerobowa)": "#F44336"
                                    }

                                    col_pie, col_bar = st.columns(2)

                                    with col_pie:
                                        fig_pie = px.pie(
                                            df_zones, 
                                            names="Strefa", 
                                            values="Czas (min)",
                                            hole=0.4, 
                                            color="Strefa", 
                                            color_discrete_map=kolory_stref, # Używamy mapy
                                            category_orders={"Strefa": list(kolory_stref.keys())}, # Wymuszamy kolejność
                                            title="Proporcje spędzonego czasu"
                                        )
                                        # Wyłączamy sortowanie po wielkości (dzięki temu legenda jest Z1 -> Z5)
                                        fig_pie.update_traces(sort=False, textposition='inside', textinfo='percent')
                                        st.plotly_chart(fig_pie, use_container_width=True)

                                    with col_bar:
                                        fig_bar = px.bar(
                                            df_zones, 
                                            x="Czas (min)", 
                                            y="Strefa", 
                                            orientation='h',
                                            color="Strefa", 
                                            color_discrete_map=kolory_stref, # Używamy tej samej mapy
                                            title="Całkowity czas w minutach", 
                                            text="Czas (min)"
                                        )
                                        fig_bar.update_layout(
                                            yaxis={'categoryorder':'array', 'categoryarray': list(reversed(kolory_stref.keys()))},
                                            showlegend=False
                                        )
                                        st.plotly_chart(fig_bar, use_container_width=True)
                                else:
                                    # Brak danych (brak tętna lub brak konta Premium)
                                    st.info("ℹ️ Brak danych o strefach tętna w wybranym okresie. Funkcja ta wymaga, aby zawodnik posiadał subskrypcję Strava Premium oraz rejestrował tętno podczas treningów.")
                        else:
                            st.warning("Brak treningów w tym okresie.")
                            
                    except Exception as e:
                        st.error(f"Wystąpił błąd: {e}")

# --- ZAKŁADKA 2: DODAWANIE (Manualne) ---
with tab2:
    st.header("Dodaj nowego podopiecznego")
    
    client = Client()
    auth_url = client.authorization_url(
        client_id=MY_CLIENT_ID,
        redirect_uri='https://td-analysis.streamlit.app/?strona=sukces',
        scope=['activity:read_all']
    )
    
    st.markdown("### Krok 1: Link autoryzacyjny")
    st.markdown("Wyślij ten link zawodnikowi:")
    st.code(auth_url)
    
    st.markdown("### Krok 2: Wklej dane")
    st.markdown("""
    1. Zawodnik klika link i loguje się.
    2. Zostaje przekierowany na stronę sukcesu.
    3. Kopiuje z pola kod.
    4. Wysyła ten kod Tobie.
    """)
    
    col_a, col_b = st.columns(2)
    code_input = col_a.text_input("Wklej kod autoryzacji (code):")
    name_input = col_b.text_input("Nazwa zawodnika (np. Janek):")
    
    if st.button("Zapisz zawodnika w bazie"):
        if code_input and name_input:
            try:
                token_response = client.exchange_code_for_token(
                    client_id=MY_CLIENT_ID,
                    client_secret=MY_CLIENT_SECRET,
                    code=code_input
                )
                
                db = load_db()
                db[name_input] = {
                    'access_token': token_response['access_token'],
                    'refresh_token': token_response['refresh_token'],
                    'expires_at': token_response['expires_at']
                }
                save_db(db)
                st.success(f"Sukces! Dodano zawodnika: {name_input}")
                
            except Exception as e:
                st.error(f"Błąd autoryzacji: {e}")
                st.warning("Sprawdź czy kod jest poprawny i czy Client ID/Secret w kodzie są dobre.")
        else:
            st.warning("Wypełnij oba pola (Kod i Nazwa).")

# --- UKRYWANIE MENU STREAMLIT ---
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;} /* Ukrywa hamburger menu z linkiem do GitHuba */
    header {visibility: hidden;}    /* Ukrywa górny pasek z przyciskiem Deploy */
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)