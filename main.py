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

import streamlit as st
from streamlit_calendar import calendar
import datetime
from streamlit_option_menu import option_menu

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
    link="https://coachplus.pl/"
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
# BRANDING I STYLIZACJA (PREMIUM DARK MODE)
# ==========================================

brand_style = """
    <style>
    /* GŁÓWNE TŁO I TEKST */
    .stApp, .main {
        background-color: #000000 !important;
        color: #f5f5f7 !important;
    }
    
    /* KARTY, EXPANDERY, FORMULARZE, BOCZNY PASEK (Tło #0a0a0c + szkliste ramki) */
    [data-testid="stSidebar"],
    div[data-testid="stExpander"] details,
    div[data-testid="metric-container"],
    div[data-testid="stForm"],
    div[role="dialog"] {
        background-color: #0a0a0c !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
    }
    
    div[data-testid="metric-container"] {
        padding: 15px !important;
    }

    /* TYPOGRAFIA (Wyciszony tekst dla labeli i mniejszych opisów) */
    p, label, .st-emotion-cache-1wivap2, .stMarkdown p {
        color: #b4b4b8 !important;
    }
    
    h1, h2, h3, h4, h5, h6, [data-testid="stMetricValue"], .stMarkdown strong {
        color: #f5f5f7 !important;
    }

    /* INPUTY I POLA FORMULARZA */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #000000 !important;
        color: #f5f5f7 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
    }

    /* PRZYCISKI PRIMARY (Zwykłe ORAZ w formularzu logowania) */
    button[kind="primary"],
    div[data-testid="stFormSubmitButton"] button {
        background-color: #4bb8ff !important;
        border: none !important;
        border-radius: 8px !important;
        transition: background-color 0.3s ease !important;
    }
    button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #339ce3 !important;
    }
    /* HACK: Brutalne wymuszenie czarnego tekstu na wszystkim wewnątrz przycisku (P, DIV, SPAN) */
    button[kind="primary"] *,
    div[data-testid="stFormSubmitButton"] button * {
        color: #000000 !important; 
        font-weight: 600 !important;
    }

    /* PRZYCISKI SECONDARY (Przezroczyste ze szklaną ramką) */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: #4bb8ff !important;
    }
    button[kind="secondary"] p {
        color: #f5f5f7 !important; 
    }
    button[kind="secondary"]:hover p {
        color: #4bb8ff !important; 
    }
    
    /* Ukrywanie menu Streamlita */
    #MainMenu {visibility: hidden;} 
    .stAppDeployButton {display: none;}
    </style>
"""
st.markdown(brand_style, unsafe_allow_html=True)


# ==========================================
# ROUTER (STEROWANIE STRONAMI)
# ==========================================

query_params = st.query_params

# --- SCENARIUSZ A: POLITYKA PRYWATNOŚCI ---
if query_params.get("strona") == "prywatnosc":

    # Przycisk powrotu
    if st.button("Wróć do aplikacji"):
        st.query_params.clear() 
        st.rerun()              

    st.markdown("""
    # Polityka Prywatności
    **Data ostatniej aktualizacji:** 17 marca 2026 r.

    Niniejsza Polityka Prywatności określa, w jaki sposób aplikacja **CoachPlus Dashboard** ("my", "nasza aplikacja") zbiera, przetwarza i chroni dane osobowe Trenerów oraz Zawodników w związku z korzystaniem z platformy i integracji z API serwisu Strava.

    ## 1. Wprowadzenie
    Aplikacja jest platformą analityczną (SaaS) stworzoną na potrzeby współpracy trenerskiej. Jej głównym celem jest bezpieczne gromadzenie i wizualizacja danych treningowych, co pozwala trenerom i zawodnikom na lepszą analizę wyników.

    ## 2. Jakie dane zbieramy?
    Nie pobieramy żadnych danych bez Twojej wyraźnej, dobrowolnej zgody. 
    
    **Jeśli jesteś Zawodnikiem (integracja ze Stravą):**
    * **Dane profilowe:** Imię i nazwisko (lub pseudonim podany trenerowi) oraz unikalne ID ze Stravy.
    * **Dane o aktywnościach:** Pobieramy i zapisujemy historię Twoich treningów, w tym: typy aktywności, dystans, czas trwania, tempo/prędkość, tętno (w tym strefy tętna) oraz daty treningów.
    * **Dane autoryzacyjne:** Tokeny dostępu niezbędne do utrzymania bezpiecznego połączenia (Webhooki) z Twoim kontem.

    **Jeśli jesteś Trenerem (korzystasz z panelu):**
    * **Dane logowania:** Adres e-mail oraz bezpiecznie zaszyfrowane hasło uwierzytelniające w systemie.

    ## 3. Jak wykorzystujemy Twoje dane?
    Zebrane dane są wykorzystywane **wyłącznie w celach szkoleniowych i analitycznych**, w tym do:
    * Generowania statystyk, tabel i wykresów w panelu aplikacji.
    * Umożliwienia Twojemu trenerowi monitorowania postępów i stref intensywności na bieżąco.
    
    **Nie wykorzystujemy** Twoich danych do celów reklamowych, marketingowych ani do żadnych innych działań komercyjnych.

    ## 4. Przechowywanie, bezpieczeństwo i izolacja danych
    **Nigdy nie sprzedajemy danych osobowych.**
    
    Wszystkie dane (w tym historia treningów oraz tokeny) są bezpiecznie przechowywane w naszej chmurowej bazie danych (Google Firebase). 
    Aplikacja wykorzystuje ścisłą **izolację danych (Multi-tenancy)**. Oznacza to, że Twoje dane treningowe są kryptograficznie przypisane wyłącznie do konta Twojego Trenera. Żaden inny trener korzystający z naszej platformy nie ma technicznej możliwości wglądu w Twój profil ani Twoje treningi. 

    ## 5. Twoje prawa i kontrola nad danymi
    Masz pełną kontrolę nad swoimi danymi:
    * **Wstrzymanie synchronizacji:** Możesz w dowolnym momencie odłączyć naszą aplikację, przechodząc do ustawień swojego konta: [Strava Settings > My Apps](https://www.strava.com/settings/apps) i klikając "Revoke Access" (Cofnij dostęp).
    * **Całkowite usunięcie z bazy:** Aby trwale usunąć swój profil oraz całą zapisaną historię treningów z naszej bazy danych, skontaktuj się ze swoim trenerem. Usunięcie profilu przez trenera z poziomu panelu powoduje natychmiastowe i bezpowrotne wykasowanie wszystkich Twoich danych z naszych serwerów.

    ## 6. Kontakt
    Jeśli masz jakiekolwiek pytania dotyczące niniejszej Polityki Prywatności, skontaktuj się z administratorem platformy:

    **Email:** intmondev@gmail.com

    ---
    *Ta aplikacja korzysta z API Strava, ale nie jest w żaden sposób sponsorowana, wspierana ani certyfikowana przez firmę Strava.*
    """)

    st.stop()

# --- SCENARIUSZ B: SUKCES PO AUTORYZACJI ---
if query_params.get("strona") == "sukces":

    # Przycisk powrotu
    if st.button("Wróć do aplikacji"):
        st.query_params.clear() 
        st.rerun()              

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
    """Wyświetla stopkę na dole strony (Zaktualizowane kolory)"""
    LINK_DO_POLITYKI = "https://app.coachplus.pl/?strona=prywatnosc"

    st.markdown(f"""
        <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #0a0a0c; /* Kolor kart */
            color: #b4b4b8; /* Wyciszony tekst */
            text-align: center;
            padding: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.08); /* Szklista ramka */
            z-index: 9999;
            font-size: 13px;
        }}
        .footer a {{
            color: #4bb8ff; /* Główny błękit */
            text-decoration: none;
            font-weight: bold;
            transition: color 0.3s;
        }}
        .footer a:hover {{
            color: #339ce3; /* Hover błękit */
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
    """Obsługa logowania i rejestracji z weryfikacją (Gated Access)"""
    if "FIREBASE_WEB_API_KEY" not in st.secrets:
        st.error("Brak klucza FIREBASE_WEB_API_KEY w secrets.toml!")
        return False

    api_key = st.secrets["FIREBASE_WEB_API_KEY"]
    
    # 🔗 Twój Ochroniarz w Google Cloud:
    ADMIN_WEBHOOK_URL = "https://europe-central2-coachplus-f651f.cloudfunctions.net/admin-action" 
    ADMIN_SECRET = "CoachPlus_Tajny_Klucz_999"

    # 1. Sprawdzamy, czy trener jest już zalogowany
    if "user_id" in st.session_state:
        with st.sidebar:
            st.markdown(f"Zalogowany jako:<br>**{st.session_state.email}**", unsafe_allow_html=True)
            if st.button("Wyloguj się", type="secondary"):
                del st.session_state["user_id"]
                del st.session_state["email"]
                st.rerun()
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    
    with col2:
        st.write("")
        st.markdown("<h2 style='text-align: center;'>Panel Trenera</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 20px;'>Zarządzaj swoimi zawodnikami w jednym miejscu</p>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["Logowanie", "Załóż konto"])
        
        # --- ZAKŁADKA LOGOWANIA (Z KŁÓDKĄ) ---
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Adres e-mail")
                password = st.text_input("Hasło", type="password")
                submit_login = st.form_submit_button("Zaloguj się", type="primary", use_container_width=True)

                if submit_login:
                    if email and password:
                        with st.spinner("Weryfikacja..."):
                            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
                            payload = {"email": email, "password": password, "returnSecureToken": True}
                            response = requests.post(url, json=payload)

                            if response.status_code == 200:
                                data = response.json()
                                sprawdzany_uid = data['localId']
                                
                                # 🛡️ SPRAWDZAMY STATUS W BAZIE PRZED WPUSZCZENIEM
                                trener_doc = fire_db.collection('trenerzy').document(sprawdzany_uid).get()
                                
                                if trener_doc.exists:
                                    status = trener_doc.to_dict().get('status', 'oczekujący')
                                    
                                    if status == 'zatwierdzony':
                                        st.session_state.user_id = sprawdzany_uid
                                        st.session_state.email = data['email']
                                        st.success("Zalogowano pomyślnie!")
                                        time.sleep(1)
                                        st.rerun()
                                    elif status == 'odrzucony':
                                        st.error("Twoje konto zostało odrzucone przez administratora.")
                                    else:
                                        st.warning("Twoje konto wciąż oczekuje na weryfikację. Spróbuj ponownie później.")
                                else:
                                    st.error("Błąd bazy: Nie znaleziono profilu trenera.")
                            else:
                                error_msg = response.json().get("error", {}).get("message", "")
                                if error_msg in ["INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD", "EMAIL_NOT_FOUND"]:
                                    st.error("Błędny adres e-mail lub hasło.")
                                else:
                                    st.error(f"Wystąpił błąd: {error_msg}")
                    else:
                        st.warning("Wpisz e-mail i hasło.")
        
        # --- ZAKŁADKA REJESTRACJI (Z WYSYŁANIEM LINKÓW) ---
        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("Podaj adres e-mail")
                reg_password = st.text_input("Stwórz hasło (min. 6 znaków)", type="password")
                reg_password_confirm = st.text_input("Powtórz hasło", type="password")
                submit_register = st.form_submit_button("Zarejestruj się", type="primary", use_container_width=True)

                if submit_register:
                    if reg_email and reg_password and reg_password_confirm:
                        if reg_password != reg_password_confirm:
                            st.error("Hasła nie są identyczne!")
                        elif len(reg_password) < 6:
                            st.error("Hasło musi mieć co najmniej 6 znaków.")
                        else:
                            with st.spinner("Tworzenie konta..."):
                                url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
                                payload = {"email": reg_email, "password": reg_password, "returnSecureToken": True}
                                response = requests.post(url, json=payload)

                                if response.status_code == 200:
                                    data = response.json()
                                    new_uid = data['localId']
                                    
                                    # 1. Zapis do bazy ze statusem "oczekujący"
                                    try:
                                        fire_db.collection('trenerzy').document(new_uid).set({
                                            'email': reg_email,
                                            'status': 'oczekujący',
                                            'data_rejestracji': firestore.SERVER_TIMESTAMP
                                        })
                                        
                                        # 2. Wysyłanie Magicznych Linków na Discord
                                        if "DISCORD_WEBHOOK" in st.secrets:
                                            link_zatwierdz = f"{ADMIN_WEBHOOK_URL}?uid={new_uid}&action=approve&key={ADMIN_SECRET}"
                                            link_odrzuc = f"{ADMIN_WEBHOOK_URL}?uid={new_uid}&action=reject&key={ADMIN_SECRET}"

                                            wiadomosc = (
                                                f"🔔 **Nowa Rejestracja w CoachPlus!**\n"
                                                f"📧 Trener: `{reg_email}`\n"
                                                f"🔑 UID: `{new_uid}`\n\n"
                                                f"✅ [ZATWIERDŹ KONTO]({link_zatwierdz})\n"
                                                f"❌ [ODRZUĆ KONTO]({link_odrzuc})"
                                            )
                                            requests.post(st.secrets["DISCORD_WEBHOOK"], json={"content": wiadomosc})

                                    except Exception as e:
                                        print(f"Błąd rejestracji: {e}")

                                    st.success("Konto założone! Poczekaj na weryfikację przez administratora.")
                                    st.balloons()
                                else:
                                    error_msg = response.json().get("error", {}).get("message", "")
                                    if error_msg == "EMAIL_EXISTS":
                                        st.error("Konto z tym adresem e-mail już istnieje!")
                                    else:
                                        st.error(f"Wystąpił błąd rejestracji: {error_msg}")
                    else:
                        st.warning("Wypełnij wszystkie pola.")
                        
    return False

def load_db():
    """Wczytuje bazę prosto z chmury Firebase (TYLKO dla zalogowanego trenera)"""
    db = {}
    try:
        # 1. Bierzemy ID trenera, który aktualnie używa aplikacji
        obecny_trener_id = st.session_state.user_id
        
        # 2. Mówimy Firebase: "Daj mi tylko dokumenty, gdzie pole trener_id to ID tego trenera"
        docs = fire_db.collection('zawodnicy-v2').where('trener_id', '==', obecny_trener_id).stream()
        
        for doc in docs:
            db[doc.id] = doc.to_dict()
    except Exception as e:
        st.error(f"Błąd odczytu z bazy chmurowej: {e}")
    return db

def save_db(db, zmieniony_zawodnik=None):
    """Zapisuje zaktualizowane tokeny w chmurze Firebase"""
    try:
        for imie, data in db.items():
            fire_db.collection('zawodnicy-v2').document(imie).set(data)
            
        if "DISCORD_WEBHOOK" in st.secrets:
            if zmieniony_zawodnik:
                wiadomosc = f"☁️ **Firebase Zaktualizowany!** (Dodano/odświeżono zawodnika: **{zmieniony_zawodnik}**)"
            else:
                wiadomosc = "☁️ **Firebase Zaktualizowany!** (Zapisano bazę)"
                
            payload = {"content": wiadomosc}
            requests.post(st.secrets["DISCORD_WEBHOOK"], json=payload)
            
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
    """Bezpiecznie wyciąga tokeny i ID zawodnika."""
    if isinstance(response, tuple):
        response = response[0]
        
    athlete_id = None
        
    if isinstance(response, dict):
        athlete_data = response.get('athlete', {})
        if isinstance(athlete_data, dict):
            athlete_id = athlete_data.get('id')
            
        return {
            'access_token': response.get('access_token'),
            'refresh_token': response.get('refresh_token'),
            'expires_at': response.get('expires_at'),
            'athlete_id': athlete_id  
        }
    else:
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
            'athlete_id': athlete_id  
        }

# ==========================================
# 🔐 URUCHOMIENIE LOGOWANIA I STOPKI
# ==========================================

render_footer()

if not check_password():
    st.stop()

# ==========================================
# OKNO MODALNE (POP-UP) Z ANALIZĄ
# ==========================================
@st.dialog("Szczegóły Treningu", width="large")
def pokaz_analize(trening_id, zawodnik_imie):
    with st.spinner("Ładowanie analizy..."):
        try:
            doc_ref = fire_db.collection('zawodnicy-v2').document(zawodnik_imie).collection('historia_treningow').document(str(trening_id))
            doc = doc_ref.get()

            if doc.exists:
                trening_dane = doc.to_dict()
                
                st.markdown(f"### {trening_dane.get('name', 'Brak nazwy')}")
                st.markdown(f"**Data:** {trening_dane.get('start_date_local', '')[:10]}")
                st.write("---")

                m1, m2, m3 = st.columns(3)
                m1.metric("Max Tętno", f"{trening_dane.get('max_heartrate', '-')} bpm")
                m2.metric("Śr. Kadencja", f"{trening_dane.get('average_cadence', '-') * 2} spm")
                m3.metric("Przewyższenie", f"{trening_dane.get('total_elevation_gain', '-')} m")
                
                st.write("---")
                
                if 'splits_metric' in trening_dane:
                    st.markdown("#### ⏱️ Splity")
                    splits = []
                    for split in trening_dane['splits_metric']:
                        speed_ms = split.get('average_speed', 0)
                        tempo_split = "-"
                        if speed_ms > 0:
                            p_dec = (1000 / speed_ms) / 60
                            tempo_split = f"{int(p_dec)}:{int((p_dec - int(p_dec)) * 60):02d}"
                            
                        splits.append({
                            "KM": split.get('split', '-'),
                            "Tempo": tempo_split,
                            "Śr. Tętno": round(split.get('average_heartrate', 0)),
                            "Wznios": split.get('elevation_difference', 0)
                        })
                    st.dataframe(pd.DataFrame(splits), width="stretch", hide_index=True)
                else:
                    st.info("Brak szczegółowych międzyczasów dla tego treningu.")
        except Exception as e:
            st.error(f"Błąd odczytu bazy: {e}")


@st.dialog("Zaplanuj jednostkę")
def dodaj_trening_dialog(zawodnik_imie):
    st.markdown(f"Planujesz trening dla: **{zawodnik_imie}**")
    
    typ_treningu = st.selectbox("Typ treningu", ["🏃‍♂️ Bieganie", "🚴‍♂️ Rower", "🏊‍♂️ Basen", "🏋️‍♂️ Siłownia", "🧘‍♂️ Regeneracja"])
    data_treningu = st.date_input("Data treningu", pd.to_datetime("today"))
    czas_trwania = st.number_input("Zakładany czas (minuty)", min_value=5, max_value=300, step=5, value=60)
    notatka = st.text_area("Notatka dla zawodnika", placeholder="Np. 4x1km w tempie startowym, przerwa 2 minuty...")
    
    if st.button("Zapisz trening w kalendarzu", type="primary", use_container_width=True):
        st.success(f"Świetnie! {typ_treningu} dodany na {data_treningu}.")
        st.info("Docelowo tutaj nastąpi zapis do Firebase.")
        # Tutaj w przyszłości dodamy zapis do bazy

# ==========================================
# GŁÓWNY INTERFEJS APLIKACJI
# ==========================================

st.title("Panel Trenera")

# WRACAMY DO ZAKŁADEK!
st.write("") # Odstęp
wybrana_zakladka = option_menu(
    menu_title=None,  # Ukrywamy tytuł menu
    options=["Analiza treningów", "Utwórz trening", "Dodaj zawodnika"],
    icons=["graph-up", "calendar-check", "person-plus"], # Piękne ikony
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#0a0a0c", "border": "1px solid rgba(255, 255, 255, 0.08)", "border-radius": "12px"},
        "icon": {"color": "#b4b4b8", "font-size": "18px"}, 
        "nav-link": {"font-size": "15px", "text-align": "center", "margin": "0px", "--hover-color": "#1a1a1c", "color": "#b4b4b8"},
        "nav-link-selected": {"background-color": "#4bb8ff", "color": "#000000", "font-weight": "bold", "icon-color": "#000000"},
    }
)
st.markdown("<br>", unsafe_allow_html=True)

# --- ZAKŁADKA 1: ANALIZA ---
if wybrana_zakladka == "Analiza treningów":
    db = load_db()
    
    if not db:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby kogoś dodać.")
    else:
        imiona = list(db.keys())
        wybrany_imie = st.selectbox("Wybierz podopiecznego:", imiona)
        
        if wybrany_imie and wybrany_imie in db:
            zawodnik_data = db[wybrany_imie]
            
            with st.expander("⚙️ Zarządzanie zawodnikiem"):
                st.warning(f"Czy na pewno chcesz usunąć zawodnika **{wybrany_imie}**? Usunięcie z bazy jest nieodwracalne.")
                if st.button(f"Ostatecznie usuń: {wybrany_imie}", type="primary"):
                    with st.spinner("Usuwam historię treningów i czyszczę bazę... 🧹"):
                        treningi_ref = fire_db.collection('zawodnicy-v2').document(wybrany_imie).collection('historia_treningow')
                        treningi_docs = treningi_ref.stream()
                        
                        licznik = 0
                        for doc in treningi_docs:
                            doc.reference.delete()
                            licznik += 1
                            
                        fire_db.collection('zawodnicy-v2').document(wybrany_imie).delete()
                    
                    if "DISCORD_WEBHOOK" in st.secrets:
                        wiadomosc_usuniecie = f"🗑️ **Zawodnik Usunięty!** (Skasowano {licznik} treningów oraz profil: **{wybrany_imie}**)"
                        requests.post(st.secrets["DISCORD_WEBHOOK"], json={"content": wiadomosc_usuniecie})
                        
                    st.success(f"Pomyślnie usunięto zawodnika i wyczyszczono jego {licznik} treningów z bazy!")
                    time.sleep(2) 
                    st.rerun()
            
            client = Client()
            
            if time.time() > zawodnik_data['expires_at']:
                try:
                    refresh_response = client.refresh_access_token(
                        client_id=MY_CLIENT_ID,
                        client_secret=MY_CLIENT_SECRET,
                        refresh_token=zawodnik_data['refresh_token']
                    )
                    nowe_dane = parse_token_response(refresh_response)
                    
                    db[wybrany_imie]['access_token'] = nowe_dane['access_token']
                    db[wybrany_imie]['refresh_token'] = nowe_dane['refresh_token']
                    db[wybrany_imie]['expires_at'] = nowe_dane['expires_at']
                    
                    save_db(db, zmieniony_zawodnik=wybrany_imie)
                except Exception as e:
                    st.error(f"Nie udało się odświeżyć tokena: {e}")

            client.access_token = db[wybrany_imie]['access_token']
            
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
            
            st.markdown("**Wybierz typy aktywności do analizy:**")
            
            c1, c2, c3 = st.columns(3)
            
            wybrane_typy = []
            if c1.checkbox("Bieganie", value=False): wybrane_typy.append("Bieganie")
            if c2.checkbox("Jazda na rowerze", value=False): wybrane_typy.append("Jazda na rowerze")
            if c3.checkbox("Pływanie", value=False): wybrane_typy.append("Pływanie")
            if c1.checkbox("Bieganie na nartach", value=False): wybrane_typy.append("Bieganie na nartach")
            if c2.checkbox("Wiosłowanie", value=False): wybrane_typy.append("Wiosłowanie")
            if c3.checkbox("Siłownia", value=False): wybrane_typy.append("Siłownia")
            if c1.checkbox("Spacer", value=False): wybrane_typy.append("Spacer")
            if c2.checkbox("Inne", value=False): wybrane_typy.append("Inne")

            if st.button("Pobierz i filtruj treningi", type="primary"):
                st.session_state.pokaz_tabele = True

            if st.session_state.get("pokaz_tabele", False):
                with st.spinner('Wczytuję dane z bazy...'):
                    try:
                        treningi_ref = fire_db.collection('zawodnicy-v2').document(wybrany_imie).collection('historia_treningow')
                        docs = treningi_ref.stream()
                        
                        data = []
                        nierozpoznane_typy = set()
                        hr_zones_aggregated = {"Z1 (Regeneracja)": 0, "Z2 (Wytrzymałość)": 0, "Z3 (Tempo)": 0, "Z4 (Próg)": 0, "Z5 (Anaerobowa)": 0}

                        for doc in docs:
                            activity = doc.to_dict()
                            
                            start_date_str = activity.get('start_date_local', '')
                            if not start_date_str: continue
                                
                            activity_date_str = start_date_str[:10]
                            activity_date = pd.to_datetime(activity_date_str).date()
                            
                            if not (start_date <= activity_date <= end_date): continue

                            raw_type_str = activity.get('sport_type') or activity.get('type', 'Unknown')
                            polski_typ = TYPE_MAP.get(raw_type_str, "Inne")
                            if polski_typ == "Inne": nierozpoznane_typy.add(raw_type_str)

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
                                "Data": activity_date_str, "Typ Polski": polski_typ, "Typ": raw_type_str,
                                "Nazwa": activity.get('name', 'Brak nazwy'), "Strava": activity_url, 
                                "Dystans (km)": dist_km, "Czas": czas_str, "Czas (min)": duration_min, 
                                "Tętno": avg_hr, "Tempo": pace_str, "ID Treningu": activity_id
                            })

                            if activity.get('has_heartrate', False) and 'zones' in activity:
                                for z in activity['zones']:
                                    if z.get('type') == 'heartrate' and 'distribution_buckets' in z:
                                        buckets = z['distribution_buckets']
                                        if len(buckets) >= 5:
                                            hr_zones_aggregated["Z1 (Regeneracja)"] += buckets[0].get('time', 0)
                                            hr_zones_aggregated["Z2 (Wytrzymałość)"] += buckets[1].get('time', 0)
                                            hr_zones_aggregated["Z3 (Tempo)"] += buckets[2].get('time', 0)
                                            hr_zones_aggregated["Z4 (Próg)"] += buckets[3].get('time', 0)
                                            hr_zones_aggregated["Z5 (Anaerobowa)"] += buckets[4].get('time', 0)
                        
                        if data:
                            df = pd.DataFrame(data)
                            df_filtered = df[df["Typ Polski"].isin(wybrane_typy)]
                            
                            if df_filtered.empty:
                                st.warning(f"Brak treningów pasujących do filtra: {wybrane_typy}")
                            else:
                                final_df = df_filtered[['Data', 'Typ', 'Nazwa', 'Dystans (km)', 'Czas', 'Czas (min)', 'Tętno', 'Tempo', 'Strava', 'ID Treningu']]
                                final_df = final_df.sort_values(by="Data", ascending=False)
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Liczba treningów", len(final_df))
                                c2.metric("Suma km", round(final_df['Dystans (km)'].sum(), 1))
                                c3.metric("Czas (h)", round(final_df['Czas (min)'].sum() / 60, 1))

                                st.write("---")

                                if "klucz_tabeli" not in st.session_state: st.session_state.klucz_tabeli = 0
                                    
                                st.markdown("**Kliknij w dowolny wiersz tabeli, aby otworzyć szczegółową analizę treningu!**")
                                
                                # 💡 TUTAJ UKRYWAMY DUPLIKAT CZASU:
                                event = st.dataframe(
                                    final_df, 
                                    key=f"tabela_{st.session_state.klucz_tabeli}", 
                                    width="stretch", 
                                    hide_index=True, 
                                    on_select="rerun", 
                                    selection_mode="single-row",
                                    column_config={
                                        "Strava": st.column_config.LinkColumn("Strava", display_text="Otwórz 🔗"), 
                                        "ID Treningu": None,
                                        "Czas (min)": None # <--- Ta linijka ukrywa kolumnę z minutami!
                                    }
                                )
                                
                                if len(event.selection.rows) > 0:
                                    wybrany_id = final_df.iloc[event.selection.rows[0]]["ID Treningu"]
                                    if st.session_state.get("ostatni_trening") != wybrany_id:
                                        st.session_state.ostatni_trening = wybrany_id
                                        st.session_state.klucz_tabeli += 1 
                                        pokaz_analize(wybrany_id, wybrany_imie)
                                else:
                                    st.session_state.ostatni_trening = None
                                
                                if "Czas (min)" in final_df.columns and final_df["Czas (min)"].sum() > 0:
                                    kolor_wg = "Typ" if len(wybrane_typy) > 1 else "Tętno"
                                    tytul = "Dzienny czas trwania aktywności" if len(wybrane_typy) > 1 else f"Dzienny czas treningu ({wybrane_typy[0]})"
                                    fig = px.bar(final_df, x="Data", y="Czas (min)", title=tytul, color=kolor_wg, hover_data=["Nazwa", "Czas", "Dystans (km)"])
                                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                                    st.plotly_chart(fig)
                                
                                # === ZAGUBIONE WYKRESY TĘTNA WRACAJĄ NA MIEJSCE ===
                                st.write("---")
                                st.subheader("Analiza stref tętna")

                                if sum(hr_zones_aggregated.values()) > 0:
                                    df_zones = pd.DataFrame({
                                        "Strefa": list(hr_zones_aggregated.keys()),
                                        "Czas (min)": [int(round(v / 60)) for v in hr_zones_aggregated.values()]
                                    })
                                    
                                    kolory_stref = {
                                        "Z1 (Regeneracja)": "#b4b4b8", # Wyciszony szary
                                        "Z2 (Wytrzymałość)": "#4bb8ff", # Twój błękit!
                                        "Z3 (Tempo)": "#4CAF50",
                                        "Z4 (Próg)": "#FF9800",
                                        "Z5 (Anaerobowa)": "#F44336"
                                    }

                                    col_pie, col_bar = st.columns(2)

                                    with col_pie:
                                        fig_pie = px.pie(
                                            df_zones, names="Strefa", values="Czas (min)",
                                            hole=0.4, color="Strefa", color_discrete_map=kolory_stref, 
                                            category_orders={"Strefa": list(kolory_stref.keys())}, 
                                            title="Proporcje spędzonego czasu"
                                        )
                                        fig_pie.update_traces(sort=False, textposition='inside', textinfo='percent')
                                        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                                        st.plotly_chart(fig_pie, width="stretch")

                                    with col_bar:
                                        fig_bar = px.bar(
                                            df_zones, x="Czas (min)", y="Strefa", orientation='h',
                                            color="Strefa", color_discrete_map=kolory_stref, 
                                            title="Całkowity czas w minutach", text="Czas (min)"
                                        )
                                        fig_bar.update_layout(
                                            yaxis={'categoryorder':'array', 'categoryarray': list(reversed(kolory_stref.keys()))},
                                            showlegend=False,
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                                        )
                                        st.plotly_chart(fig_bar, width="stretch")
                                else:
                                    st.info("Brak danych o strefach tętna w wybranym okresie. Funkcja ta wymaga, aby zawodnik posiadał subskrypcję Strava Premium oraz rejestrował tętno podczas treningów.")
                        else:
                            st.warning("Brak treningów w tym okresie.")
                    except Exception as e:
                        st.error(f"Wystąpił błąd: {e}")

# --- ZAKŁADKA 2: KREATOR TRENINGÓW ---
elif wybrana_zakladka == "Utwórz trening":
    st.markdown("### Zaplanuj jednostki treningowe")
    
    db_kreator = load_db()
    if not db_kreator:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby móc układać plany.")
    else:
        imiona_kreator = list(db_kreator.keys())
        wybrany_zawodnik_plan = st.selectbox("Wybierz podopiecznego:", imiona_kreator, key="kreator_wybor_zawodnika")
        
        st.divider()

        col_btn, col_puste = st.columns([1, 3])
        with col_btn:
            if st.button("➕ Dodaj trening", type="primary", use_container_width=True):
                dodaj_trening_dialog(wybrany_zawodnik_plan)

        st.write("")

        # Parametry kalendarza
        calendar_options = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridMonth,dayGridWeek"
            },
            "initialView": "dayGridMonth",
            "height": 650,
            "locale": "pl",       
            "firstDay": 1,        
            "editable": True,     
            
            "displayEventTime": False, 
            
            "views": {
                "dayGridMonth": {"dayHeaderFormat": {"weekday": "long"}},
                "dayGridWeek": {"dayHeaderFormat": {"weekday": "short", "day": "2-digit", "month": "2-digit", "omitCommas": True}}
            }
        }

        dzisiaj_str = str(pd.to_datetime("today").date())
        
        mock_events = [
            # Dwa treningi w TEN SAM dzień (z ukrytym czasem dla odpowiedniego sortowania)
            {"title": "Basen (Rano)", "start": f"{dzisiaj_str}T16:00:00", "color": "#1565c0"},
            {"title": "Rower (Wieczór)", "start": f"{dzisiaj_str}T18:00:00", "color": "#d32f2f"},
            
            # Trening na jutro
            {"title": "Rozbieganie", "start": str((pd.to_datetime("today") + pd.Timedelta(days=1)).date()), "color": "#2e7b32"}
        ]

        try:
            # Dodaliśmy klucz (key="kalendarz_kreator"), co czasami wymusza renderowanie w st.tabs
            kalendarz_widżet = calendar(
                events=mock_events, 
                options=calendar_options, 
                custom_css="""
                    .fc-event-title { font-weight: 600; font-size: 14px; padding: 2px; }
                    .fc-toolbar-title { font-weight: bold; }
                """,
                key="kalendarz_kreator"
            )
        except Exception as e:
            st.error(f"Błąd ładowania kalendarza: {e}")

# --- ZAKŁADKA 3: DODAWANIE ---
elif wybrana_zakladka == "Dodaj zawodnika":
    st.header("Dodaj nowego podopiecznego")
    
    client = Client()
    auth_url = client.authorization_url(
        client_id=MY_CLIENT_ID,
        redirect_uri='https://app.coachplus.pl/?strona=sukces',
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
    
    if st.button("Zapisz zawodnika w bazie", type="primary"):
        if code_input and name_input:
            try:
                token_response = client.exchange_code_for_token(client_id=MY_CLIENT_ID, client_secret=MY_CLIENT_SECRET, code=code_input)
                nowe_dane = parse_token_response(token_response)
                athlete_id = nowe_dane.get('athlete_id')
                
                if not athlete_id:
                    headers = {'Authorization': f"Bearer {nowe_dane['access_token']}"}
                    res = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
                    if res.status_code == 200: athlete_id = res.json().get('id')

                db = load_db()
                db[name_input] = {
                    'athlete_id': athlete_id, 'access_token': nowe_dane['access_token'],
                    'refresh_token': nowe_dane['refresh_token'], 'expires_at': nowe_dane['expires_at'],
                    'trener_id': st.session_state.user_id
                }
                save_db(db, zmieniony_zawodnik=name_input)
                st.success(f"Sukces! Dodano zawodnika: {name_input} (ID: {athlete_id})")

                with st.spinner('Pobieram historię treningów z ostatnich 14 dni...'):
                    try:
                        headers = {'Authorization': f"Bearer {nowe_dane['access_token']}"}
                        res_activities = requests.get('https://www.strava.com/api/v3/athlete/activities', headers=headers, params={'after': int(time.time()) - (14 * 24 * 3600), 'per_page': 50})
                        
                        if res_activities.status_code == 200:
                            activities_list = res_activities.json()
                            user_ref = fire_db.collection('zawodnicy-v2').document(name_input)
                            zapisane_treningi = 0
                            
                            for act in activities_list:
                                act_id = act.get('id')
                                res_detail = requests.get(f'https://www.strava.com/api/v3/activities/{act_id}', headers=headers)
                                if res_detail.status_code == 200:
                                    full_act = res_detail.json()
                                    if full_act.get('has_heartrate'):
                                        res_zones = requests.get(f'https://www.strava.com/api/v3/activities/{act_id}/zones', headers=headers)
                                        if res_zones.status_code == 200: full_act['zones'] = res_zones.json()
                                    user_ref.collection('historia_treningow').document(str(act_id)).set(full_act)
                                    zapisane_treningi += 1
                                else:
                                    user_ref.collection('historia_treningow').document(str(act_id)).set(act)
                                
                            st.success(f"Baza gotowa! Zapisano {zapisane_treningi} treningów z historii.")
                            time.sleep(2)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Błąd pobierania historii: {e}")
            except Exception as e:
                st.error(f"Błąd autoryzacji: {e}")
        else:
            st.warning("Wypełnij oba pola (Kod i Nazwa).")