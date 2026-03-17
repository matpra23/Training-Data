import streamlit as st
from stravalib.client import Client
import pandas as pd
import plotly.express as px
import json
import os
import time


import requests
import firebase_admin
from firebase_admin import credentials, firestore

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
DB_FILE = 'zawodnicy-v2.json'

# Logo aplikacji
st.logo(
    "intmon.png",
    icon_image="intmon.png",
)

# --- INICJALIZACJA BAZY FIREBASE ---
if not firebase_admin._apps:
    # Pobieramy nasz klucz [firebase] z sekretów
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

# Skrót do naszej chmurowej bazy
fire_db = firestore.client()

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
    # Polityka Prywatności
    **Data ostatniej aktualizacji:** 3 marca 2026 r.

    Niniejsza Polityka Prywatności określa, w jaki sposób aplikacja **CoachPlus Dashboard** ("my", "nasza aplikacja") zbiera, przetwarza i chroni Twoje dane osobowe w związku z korzystaniem z integracji z API serwisu Strava.

    ## 1. Wprowadzenie
    Aplikacja jest wewnętrznym narzędziem analitycznym stworzonym na potrzeby współpracy trenerskiej. Jej głównym celem jest wizualizacja danych treningowych, co pozwala trenerom i zawodnikom na lepszą analizę wyników oraz precyzyjne dostosowywanie planów treningowych.

    ## 2. Jakie dane zbieramy?
    Nie pobieramy żadnych Twoich danych bez Twojej wyraźnej, dobrowolnej zgody. Po autoryzacji naszej aplikacji za pośrednictwem serwisu Strava, uzyskujemy dostęp do następujących informacji:
    * **Dane profilowe:** Imię i nazwisko (lub pseudonim podany trenerowi).
    * **Dane o aktywnościach:** Typy aktywności (bieganie, rower, pływanie itp.), dystans, czas trwania, tempo/prędkość, tętno (w tym strefy tętna) oraz daty treningów.
    * **Dane autoryzacyjne:** Tokeny dostępu (klucze API) niezbędne do utrzymania bezpiecznego połączenia z Twoim kontem.

    ## 3. Jak wykorzystujemy Twoje dane?
    Zebrane dane są wykorzystywane **wyłącznie w celach szkoleniowych i analitycznych**, w tym do:
    * Generowania statystyk, tabel i wykresów w panelu aplikacji.
    * Umożliwienia Twojemu trenerowi monitorowania postępów, obciążeń treningowych oraz stref intensywności.
    
    **Nie wykorzystujemy** Twoich danych do celów reklamowych, marketingowych ani do żadnych innych działań komercyjnych niezwiązanych bezpośrednio z usługą trenerską.

    ## 4. Przechowywanie i udostępnianie danych
    **Nigdy nie sprzedajemy Twoich danych osobowych.**
    
    Szczegółowe dane dotyczące Twoich treningów nie są trwale magazynowane na naszych serwerach – są pobierane i przetwarzane w czasie rzeczywistym na żądanie trenera. 
    W naszej bezpiecznej chmurowej bazie danych (Google Firebase) przechowujemy wyłącznie Twoją nazwę użytkownika oraz tokeny autoryzacyjne, które pozwalają aplikacji na komunikację ze Stravą. Nie udostępniamy tych danych żadnym podmiotom trzecim, z wyjątkiem sytuacji wymaganych przez prawo.

    ## 5. Twoje prawa i kontrola nad danymi
    Masz pełną kontrolę nad swoimi danymi i w każdej chwili możesz zrezygnować z integracji:
    * **Cofnięcie dostępu:** Możesz w dowolnym momencie odłączyć naszą aplikację, przechodząc do ustawień swojego konta: [Strava Settings > My Apps](https://www.strava.com/settings/apps) i klikając "Revoke Access" (Cofnij dostęp).
    * **Całkowite usunięcie z bazy:** Aby trwale usunąć swoje imię oraz wygasłe tokeny z bazy danych aplikacji, skontaktuj się bezpośrednio ze swoim trenerem, który usunie Twój profil jednym kliknięciem z poziomu panelu.

    ## 6. Kontakt
    Jeśli masz jakiekolwiek pytania dotyczące niniejszej Polityki Prywatności, skontaktuj się z administratorem/deweloperem aplikacji:

    **Email:** intmondev@gmail.com

    ---
    *Ta aplikacja korzysta z API Strava, ale nie jest w żaden sposób sponsorowana, wspierana ani certyfikowana przez firmę Strava.*
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
                | Using Strava API 
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
# 
def load_db():
    """Wczytuje bazę prosto z chmury Firebase (Firestore)"""
    db = {}
    try:
        # Pobieramy wszystkich dokumenty (zawodników) z kolekcji "zawodnicy"
        docs = fire_db.collection('zawodnicy-v2').stream()
        for doc in docs:
            db[doc.id] = doc.to_dict()
    except Exception as e:
        st.error(f"Błąd odczytu z bazy chmurowej: {e}")
    return db

def save_db(db, zmieniony_zawodnik=None):
    """Zapisuje zaktualizowane tokeny w chmurze Firebase"""
    try:
        # Zapisujemy lub aktualizujemy dane każdego zawodnika w kolekcji
        for imie, data in db.items():
            fire_db.collection('zawodnicy-v2').document(imie).set(data)
            
        # Zostawiamy powiadomienie na Discordzie ze szczegółami
        if "DISCORD_WEBHOOK" in st.secrets:
            if zmieniony_zawodnik:
                wiadomosc = f"☁️ **Firebase Zaktualizowany!** (Dodano/odświeżono zawodnika: **{zmieniony_zawodnik}**)"
            else:
                wiadomosc = "☁️ **Firebase Zaktualizowany!** (Zapisano bazę)"
                
            payload = {"content": wiadomosc}
            requests.post(st.secrets["DISCORD_WEBHOOK"], json=payload)
            
    except Exception as e:
        st.error(f"🚨 Błąd zapisu do bazy chmurowej: {e}")
            
    except Exception as e:
        st.error(f"🚨 Błąd zapisu do bazy chmurowej: {e}")

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

def parse_token_response(response):
    """Bezpiecznie wyciąga tokeny i ID zawodnika, niezależnie od tego, czy stravalib zwróci słownik, czy obiekt."""
    if isinstance(response, tuple):
        response = response[0]
        
    # Przygotowujemy zmienną na ID
    athlete_id = None
        
    if isinstance(response, dict):
        # Wyciąganie ID ze słownika
        athlete_data = response.get('athlete', {})
        if isinstance(athlete_data, dict):
            athlete_id = athlete_data.get('id')
            
        return {
            'access_token': response.get('access_token'),
            'refresh_token': response.get('refresh_token'),
            'expires_at': response.get('expires_at'),
            'athlete_id': athlete_id  # <--- Dodane pole!
        }
    else:
        # Wyciąganie ID z obiektu
        athlete_data = getattr(response, 'athlete', None)
        if athlete_data:
            if isinstance(athlete_data, dict):
                athlete_id = athlete_data.get('id')
            else:
                athlete_id = getattr(athlete_data, 'id', None)
                
        return {
            'access_token': getattr(response, 'access_token', None),
            'refresh_token': getattr(response, 'refresh_token', None),
            'expires_at': getattr(response, 'expires_at', None),
            'athlete_id': athlete_id  # <--- Dodane pole!
        }

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

tab1, tab2 = st.tabs(["Analiza Treningów", "Dodaj Zawodnika"])

# --- ZAKŁADKA 1: ANALIZA ---
with tab1:
    db = load_db()
    
    if not db:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby kogoś dodać.")
    else:
        imiona = list(db.keys())
        
        wybrany_imie = st.selectbox("Wybierz podopiecznego:", imiona)
        
        if wybrany_imie and wybrany_imie in db:
            zawodnik_data = db[wybrany_imie]
            
            # --- BEZPIECZNA STREFA USUWANIA UŻYTKOWNIKÓW---
            with st.expander("⚙️ Zarządzanie zawodnikiem"):
                st.warning(f"Czy na pewno chcesz usunąć zawodnika **{wybrany_imie}**? Usunięcie z bazy jest nieodwracalne.")
                if st.button(f"🗑️ Ostatecznie usuń: {wybrany_imie}", type="primary"):
                    # 1. Usuwamy dokument prosto z chmury!
                    fire_db.collection('zawodnicy-v2').document(wybrany_imie).delete()
                    
                    # 2. Powiadomienie na Discordzie
                    if "DISCORD_WEBHOOK" in st.secrets:
                        wiadomosc_usuniecie = f"🗑️ **Zawodnik Usunięty!** (Trwale wykasowano z bazy: **{wybrany_imie}**)"
                        requests.post(st.secrets["DISCORD_WEBHOOK"], json={"content": wiadomosc_usuniecie})
                        
                    st.rerun()
            
            client = Client()
            
            # Automatyczne odświeżanie tokena
            if time.time() > zawodnik_data['expires_at']:
                try:
                    refresh_response = client.refresh_access_token(
                        client_id=MY_CLIENT_ID,
                        client_secret=MY_CLIENT_SECRET,
                        refresh_token=zawodnik_data['refresh_token']
                    )
                    
                    # Bezpieczne wyciągnięcie danych
                    nowe_dane = parse_token_response(refresh_response)
                    
                    db[wybrany_imie]['access_token'] = nowe_dane['access_token']
                    db[wybrany_imie]['refresh_token'] = nowe_dane['refresh_token']
                    db[wybrany_imie]['expires_at'] = nowe_dane['expires_at']
                    
                    save_db(db, zmieniony_zawodnik=wybrany_imie)
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
                with st.spinner('Błyskawicznie wczytuję dane z bazy... ⚡'):
                    try:
                        # 1. ODCINAMY STRAVĘ, CZYTAMY Z FIREBASE!
                        treningi_ref = fire_db.collection('zawodnicy-v2').document(wybrany_imie).collection('historia_treningow')
                        docs = treningi_ref.stream()
                        
                        data = []
                        nierozpoznane_typy = set()
                        
                        # Zostawiamy licznik stref tętna, żeby nie zepsuć wykresów niżej.
                        # UWAGA: Strava wymaga na strefy osobnego zapytania. Dodamy to wkrótce!
                        hr_zones_aggregated = {
                            "Z1 (Regeneracja)": 0, "Z2 (Wytrzymałość)": 0, "Z3 (Tempo)": 0,
                            "Z4 (Próg)": 0, "Z5 (Anaerobowa)": 0
                        }

                        for doc in docs:
                            # Zamieniamy dokument z Firebase na słownik Pythona (JSON)
                            activity = doc.to_dict()
                            
                            # --- FILTROWANIE PO DACIE ---
                            start_date_str = activity.get('start_date_local', '')
                            if not start_date_str:
                                continue
                                
                            # Konwertujemy tekst "2026-03-10T15:30:00Z" na samą datę "2026-03-10"
                            activity_date_str = start_date_str[:10]
                            activity_date = pd.to_datetime(activity_date_str).date()
                            
                            # Jeśli data nie mieści się w filtrze z suwaków, pomijamy ten trening
                            if not (start_date <= activity_date <= end_date):
                                continue

                            # --- 1. POBIERANIE TYPU ---
                            # (Czytamy ze słownika, a nie z obiektu stravalib)
                            raw_type_str = activity.get('sport_type') or activity.get('type', 'Unknown')
                            polski_typ = TYPE_MAP.get(raw_type_str, "Inne")
                            
                            if polski_typ == "Inne":
                                nierozpoznane_typy.add(raw_type_str)

                            # --- 2. PRZELICZANIE DANYCH ---
                            dist_km = round(activity.get('distance', 0) / 1000, 2)
                            
                            duration_sec = activity.get('moving_time', 0)
                            duration_min = int(round(duration_sec / 60)) 
                            
                            h = int(duration_sec // 3600)
                            m = int((duration_sec % 3600) // 60)
                            s = int(duration_sec % 60)
                            czas_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

                            avg_hr = round(activity.get('average_heartrate', 0))
                            
                            avg_speed_ms = activity.get('average_speed', 0)
                            pace_str = "-"
                            
                            if avg_speed_ms > 0:
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

                            activity_id = activity.get('id')
                            activity_url = f"https://www.strava.com/activities/{activity_id}"
                            
                            data.append({
                                "Data": activity_date_str,
                                "Typ Polski": polski_typ,
                                "Typ": raw_type_str,
                                "Nazwa": activity.get('name', 'Brak nazwy'),
                                "Dystans (km)": dist_km,
                                "Czas": czas_str,            
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
                                    'Dystans (km)', 'Czas', 'Czas (min)', 'Tętno', 'Tempo'
                                ]]
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Liczba treningów", len(final_df))
                                c2.metric("Suma km", round(final_df['Dystans (km)'].sum(), 1))
                                c3.metric("Czas (h)", round(final_df['Czas (min)'].sum() / 60, 1))

                                st.write("---")
                                
                                # W tabeli ukrywamy brzydką, suchą liczbę "Czas (min)"
                                tabela_html = final_df.drop(columns=['Czas (min)']).to_html(escape=False, index=False)
                                st.markdown(tabela_html, unsafe_allow_html=True)
                                
                                # --- WYKRES CZASU TRENINGU ---
                                if "Czas (min)" in final_df.columns and final_df["Czas (min)"].sum() > 0:
                                    
                                    # INTELIGENTNE KOLOROWANIE:
                                    if len(wybrane_typy) > 1:
                                        kolor_wg = "Typ" 
                                        tytul_wykresu = "Dzienny czas trwania aktywności"
                                    else:
                                        # Skoro na osi Y jest czas, pokolorujmy słupki na podstawie intensywności (Tętna)
                                        kolor_wg = "Tętno" 
                                        tytul_wykresu = f"Dzienny czas treningu ({wybrane_typy[0]})"

                                    fig = px.bar(
                                        final_df, 
                                        x="Data", 
                                        y="Czas (min)", # <--- ZMIANA TUTAJ
                                        title=tytul_wykresu, 
                                        color=kolor_wg,
                                        # Dodaliśmy dystans do "dymka" z informacjami po najechaniu myszką!
                                        hover_data=["Nazwa Treningu", "Czas", "Dystans (km)", "Tempo", "Tętno"]
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
                                        "Czas (min)": [int(round(v / 60)) for v in hr_zones_aggregated.values()]
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
    2. Zostaje przekierowany na stronę z kodem.
    3. Kopiuje z pola kod.
    4. Wysyła ten kod Tobie.
    """)
    
    col_a, col_b = st.columns(2)
    code_input = col_a.text_input("Wklej kod autoryzacji (code):")
    name_input = col_b.text_input("Nazwa zawodnika (np. Janek):")
    
    if st.button("Zapisz zawodnika w bazie"):
        if code_input and name_input:
            try:
                # 1. Wymiana kodu na tokeny
                token_response = client.exchange_code_for_token(
                    client_id=MY_CLIENT_ID,
                    client_secret=MY_CLIENT_SECRET,
                    code=code_input
                )
                
                # Bezpieczne wyciągnięcie samych tokenów
                nowe_dane = parse_token_response(token_response)
                
                # --- 2. KULOODPORNE POBIERANIE ID ---
                # Używamy świeżego tokena, żeby zapytać Stravę, kim jest ten człowiek!
                athlete_id = nowe_dane.get('athlete_id')
                
                if not athlete_id: # Jeśli stravalib nam tego nie dał, bierzemy to sami
                    headers = {'Authorization': f"Bearer {nowe_dane['access_token']}"}
                    res = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
                    if res.status_code == 200:
                        dane_ze_stravy = res.json()
                        athlete_id = dane_ze_stravy.get('id')
                    else:
                        st.warning("Uwaga: Udało się pobrać tokeny, ale Strava nie oddała ID zawodnika.")

                # 3. Zapis do naszej bazy Firebase
                db = load_db()
                db[name_input] = {
                    'athlete_id': athlete_id,  # Teraz mamy 100% pewności, że to tu będzie!
                    'access_token': nowe_dane['access_token'],
                    'refresh_token': nowe_dane['refresh_token'],
                    'expires_at': nowe_dane['expires_at']
                }
                save_db(db, zmieniony_zawodnik=name_input)
                st.success(f"Sukces! Dodano zawodnika: {name_input} (ID: {athlete_id})")

                # 4. AUTOMATYCZNE POBIERANIE HISTORII (2 TYGODNIE)
                with st.spinner('Pobieram historię treningów z ostatnich 14 dni...'):
                    try:
                        # Obliczamy timestamp dla daty 14 dni temu
                        dwa_tygodnie_temu = int(time.time()) - (14 * 24 * 3600)
                        
                        headers = {'Authorization': f"Bearer {nowe_dane['access_token']}"}
                        
                        # Pobieramy listę aktywności zawodnika od tej daty
                        res_activities = requests.get(
                            'https://www.strava.com/api/v3/athlete/activities',
                            headers=headers,
                            params={'after': dwa_tygodnie_temu, 'per_page': 50}
                        )
                        
                        if res_activities.status_code == 200:
                            activities_list = res_activities.json()
                            
                            # Referencja do teczki tego zawodnika w bazie
                            user_ref = fire_db.collection('zawodnicy-v2').document(name_input)
                            
                            zapisane_treningi = 0
                            
                            for act in activities_list:
                                act_id = act.get('id')
                                
                                # Pobieramy pełne detale treningu, żeby mieć to samo co w Webhooku!
                                res_detail = requests.get(f'https://www.strava.com/api/v3/activities/{act_id}', headers=headers)
                                
                                if res_detail.status_code == 200:
                                    full_act = res_detail.json()
                                    # Zapisujemy do podkolekcji historia_treningow
                                    user_ref.collection('historia_treningow').document(str(act_id)).set(full_act)
                                else:
                                    # W razie błędu zapisujemy chociaż wersję skróconą
                                    user_ref.collection('historia_treningow').document(str(act_id)).set(act)
                                    
                                zapisane_treningi += 1
                                
                            st.success(f"✅ Baza gotowa! Zapisano {zapisane_treningi} treningów z historii.")
                        else:
                            st.warning("Nie udało się pobrać historii ze Stravy.")
                            
                    except Exception as e:
                        st.error(f"Błąd podczas pobierania historii: {e}")
                
            except Exception as e:
                st.error(f"Błąd autoryzacji: {e}")
                st.warning("Sprawdź czy kod jest poprawny i czy Client ID/Secret w kodzie są dobre.")
        else:
            st.warning("Wypełnij oba pola (Kod i Nazwa).")

# --- UKRYWANIE MENU STREAMLIT ---
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;} /* Ukrywa hamburger menu z linkiem do GitHuba */
    .stAppDeployButton {display: none;} /* Ukrywa TYLKO przycisk Deploy, chroniąc logo */
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)