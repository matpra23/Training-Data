import streamlit as st
from stravalib.client import Client
import pandas as pd
import plotly.express as px
import json
import os
import time

# --- KONFIGURACJA ---
try:
    # Próba pobrania z sekretów chmurowych (Streamlit Cloud)
    MY_CLIENT_ID = st.secrets["MY_CLIENT_ID"]
    MY_CLIENT_SECRET = st.secrets["MY_CLIENT_SECRET"]
except FileNotFoundError:
    # Fallback dla działania lokalnego (jeśli nie masz pliku secrets.toml na dysku)
    # Możesz tu wpisać na sztywno DO TESTÓW LOKALNYCH, ale nie wysyłaj tego na GitHuba!
    # Lepiej stwórz lokalnie folder .streamlit/secrets.toml
    st.error("Brak skonfigurowanych sekretów!")

DB_FILE = 'zawodnicy.json'

st.set_page_config(page_title="Trener Pro (Cockpit)", layout="wide")

# --- LOGOWANIE DO APLIKACJI ---
def check_password():
    """Zwraca True jeśli użytkownik jest zalogowany, w przeciwnym razie wyświetla formularz."""
    
    # Czy mamy hasło w sekretach?
    if "APP_PASSWORD" not in st.secrets:
        st.error("Nie skonfigurowano hasła w secrets.toml!")
        return False

    # Czy użytkownik już wpisał dobre hasło w tej sesji?
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Formularz logowania
    st.markdown("## Panel - Logowanie")
    password = st.text_input("Podaj hasło dostępu", type="password")
    
    if st.button("Zaloguj"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()  # Odświeżamy stronę, żeby pokazać treść
        else:
            st.error("Błędne hasło")
            
    return False

# --- BLOKADA APLIKACJI ---
# Jeśli check_password zwróci False (niezalogowany), zatrzymujemy kod!
if not check_password():
    st.stop()


# --- FUNKCJE POMOCNICZE ---

def load_db():
    """Wczytuje bazę zawodników"""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    """Zapisuje bazę zawodników"""
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def extract_number(value, type_hint="number"):
    """Pancerna funkcja do wyciągania liczb z dziwnych obiektów Stravy"""
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    
    # Obsługa czasu (sekundy)
    if type_hint == "time":
        if hasattr(value, 'total_seconds'): return value.total_seconds()
        if hasattr(value, 'seconds'): return value.seconds
        
    # Obsługa jednostek (metry, m/s itp.)
    if hasattr(value, 'magnitude'): return float(value.magnitude)
    if hasattr(value, 'num'): return float(value.num)
    
    try: return float(value)
    except: return 0.0

# --- INTERFEJS APLIKACJI ---

st.title("Centrum Trenera")

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
            
            # --- KONFIGURACJA FILTRÓW I DAT ---
            st.write("---")
            st.subheader("Ustawienia analizy")
            
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Data początkowa", value=pd.to_datetime("today") - pd.Timedelta(days=7))
            end_date = col2.date_input("Data końcowa", value=pd.to_datetime("today"))

            # SŁOWNIK TŁUMACZEŃ (Potrzebny nadal do FILTROWANIA)
            TYPE_MAP = {
                "Run": "Bieganie",
                "VirtualRun": "Bieganie",
                "TrailRun": "Bieganie",
                "Ride": "Jazda na rowerze",
                "VirtualRide": "Jazda na rowerze",
                "EBikeRide": "Jazda na rowerze",
                "GravelRide": "Jazda na rowerze",
                "MountainBikeRide": "Jazda na rowerze",
                "Swim": "Pływanie",
                "Walk": "Spacer",
                "Hike": "Wędrówka",
                "WeightTraining": "Siłownia",
                "Workout": "Trening",
                "Yoga": "Joga"
            }
            
            mozliwe_typy = ["Bieganie", "Jazda na rowerze", "Pływanie", "Spacer", "Siłownia", "Inne"]
            wybrane_typy = st.multiselect(
                "Wybierz typy aktywności do analizy:",
                options=mozliwe_typy,
                default=["Bieganie", "Jazda na rowerze", "Pływanie"]
            )

            if st.button("Pobierz i filtruj treningi"):
                with st.spinner('Pobieram i przetwarzam dane...'):
                    try:
                        activities = client.get_activities(after=str(start_date), before=str(end_date), limit=100)
                        
                        data = []
                        nierozpoznane_typy = set()

                        for activity in activities:
                            # 1. POBIERANIE TYPU (Czyste)
                            raw_type = getattr(activity, 'sport_type', None)
                            if not raw_type:
                                raw_type = activity.type
                            
                            # Czyszczenie nazwy (usuwanie root=', ActivityType. itp.)
                            raw_type_str = str(raw_type)\
                                .replace("root='", "")\
                                .replace("'", "")\
                                .replace("ActivityType.", "")
                            
                            # Tłumaczenie (tylko do filtra!)
                            polski_typ = TYPE_MAP.get(raw_type_str, "Inne")
                            
                            if polski_typ == "Inne":
                                nierozpoznane_typy.add(raw_type_str)

                            # 2. Przeliczanie danych
                            dist_km = round(extract_number(activity.distance) / 1000, 2)
                            duration_min = round(extract_number(activity.moving_time, "time") / 60, 2)
                            avg_hr = round(extract_number(activity.average_heartrate))
                            
                            # Tempo
                            avg_speed_ms = extract_number(activity.average_speed)
                            pace_str = "-"
                            if avg_speed_ms > 0:
                                if polski_typ == "Bieganie":
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

                            activity_url = f"https://www.strava.com/activities/{activity.id}"
                            
                            data.append({
                                "Data": activity.start_date_local.strftime("%Y-%m-%d"),
                                "Typ Polski": polski_typ, # Używamy tylko do filtra, potem wyrzucimy
                                "Typ": raw_type_str,      # To chcemy wyświetlać (np. VirtualRide)
                                "Nazwa": activity.name,
                                "Dystans (km)": dist_km,
                                "Czas (min)": duration_min,
                                "Tętno": avg_hr,
                                "Tempo": pace_str,
                                "Link": activity_url
                            })
                        
                        # --- DIAGNOSTYKA ---
                        if nierozpoznane_typy:
                            st.warning(f"⚠️ Znaleziono nowe typy: {nierozpoznane_typy}")

                        if data:
                            df = pd.DataFrame(data)
                            
                            # 1. FILTROWANIE (po polskiej nazwie)
                            df_filtered = df[df["Typ Polski"].isin(wybrane_typy)]
                            
                            if df_filtered.empty:
                                st.warning(f"Brak treningów pasujących do filtra: {wybrane_typy}")
                            else:
                                # 2. PRZYGOTOWANIE TABELI (Wybieramy kolumny do wyświetlenia)
                                # Link HTML
                                df_filtered['Nazwa Treningu'] = df_filtered.apply(
                                    lambda x: f'<a href="{x["Link"]}" target="_blank" style="text-decoration:none; color:#FC4C02; font-weight:bold;">{x["Nazwa"]}</a>', 
                                    axis=1
                                )

                                # Tu definiujemy co widać. Bierzemy "Typ" (czyli VirtualRide), a nie "Typ Polski"
                                final_df = df_filtered[[
                                    'Data', 
                                    'Typ',            # <-- To jest ten oryginalny (VirtualRide)
                                    'Nazwa Treningu', 
                                    'Dystans (km)', 
                                    'Czas (min)', 
                                    'Tętno', 
                                    'Tempo'
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
                                
                                # --- WYKRES TĘTNA (POPRAWIONY) ---
                                # Sprawdzamy tylko czy mamy dane o tętnie (usuwamy warunek len == 1)
                                if "Tętno" in final_df.columns and final_df["Tętno"].sum() > 0:
                                    
                                    # INTELIGENTNE KOLOROWANIE:
                                    # Jeśli wybrano wiele sportów -> koloruj wg typu (np. Rower vs Bieg)
                                    # Jeśli wybrano jeden sport -> koloruj wg dystansu (cieniowanie)
                                    if len(wybrane_typy) > 1:
                                        kolor_wg = "Typ" 
                                        tytul_wykresu = "Średnie tętno (Podział na sporty)"
                                    else:
                                        kolor_wg = "Dystans (km)"
                                        tytul_wykresu = f"Średnie tętno ({wybrane_typy[0]})"

                                    fig = px.bar(
                                        final_df, 
                                        x="Data", 
                                        y="Tętno", 
                                        title=tytul_wykresu, 
                                        color=kolor_wg,
                                        hover_data=["Nazwa Treningu", "Tempo"] # Co widać po najechaniu myszką
                                    )
                                    st.plotly_chart(fig)
                                    
                        else:
                            st.warning("Brak treningów w tym okresie.")
                            
                    except Exception as e:
                        st.error(f"Wystąpił błąd: {e}")

# --- ZAKŁADKA 2: DODAWANIE (Manualne) ---
with tab2:
    st.header("Dodaj nowego podopiecznego")
    
    client = Client()
    # Generujemy link, który przekieruje na localhost (gdzie widać kod w pasku adresu)
    auth_url = client.authorization_url(
        client_id=MY_CLIENT_ID,
        redirect_uri='https://matpra23.github.io/Training-Data/',
        scope=['activity:read_all']
    )
    
    st.markdown("### Krok 1: Link autoryzacyjny")
    st.markdown("Wyślij ten link zawodnikowi:")
    st.code(auth_url)
    
    st.markdown("### Krok 2: Wklej dane")
    st.markdown("""
    1. Zawodnik klika link i loguje się.
    2. Zostaje przekierowany na stronę błędu ("Witryna nieosiągalna").
    3. Kopiuje z paska adresu przeglądarki fragment po **code=** (np. `a1b2c3...`).
    4. Wysyła ten kod Tobie.
    """)
    
    col_a, col_b = st.columns(2)
    code_input = col_a.text_input("Wklej kod autoryzacji (code):")
    name_input = col_b.text_input("Nazwa zawodnika (np. Janek):")
    
    if st.button("Zapisz zawodnika w bazie"):
        if code_input and name_input:
            try:
                # Wymiana kodu na token
                token_response = client.exchange_code_for_token(
                    client_id=MY_CLIENT_ID,
                    client_secret=MY_CLIENT_SECRET,
                    code=code_input
                )
                
                # Zapis do bazy
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