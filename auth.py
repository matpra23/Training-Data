import streamlit as st
import requests
import time
from database import fire_db, firestore
from config import get_env_or_secret  # Nasz bezpieczny włącznik!

ADMIN_WEBHOOK_URL = "https://europe-central2-coachplus-f651f.cloudfunctions.net/admin-action" 
ADMIN_SECRET = "CoachPlus_Tajny_Klucz_999"

def check_password():
    """Obsługa logowania i rejestracji z weryfikacją (Gated Access)"""
    
    # 1. Używamy naszej bezpiecznej funkcji zamiast bezpośredniego st.secrets
    api_key = get_env_or_secret("FIREBASE_WEB_API_KEY")
    
    if not api_key:
        st.error("Brak klucza FIREBASE_WEB_API_KEY w środowisku lub secrets.toml!")
        return False

    # Sprawdzamy, czy trener jest już zalogowany
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
        
        akcja = st.query_params.get("akcja", "logowanie")
        
        if akcja == "rejestracja":
            zakladki = st.tabs(["Załóż konto", " Logowanie"])
            tab_register = zakladki[0] 
            tab_login = zakladki[1]
        else:
            zakladki = st.tabs(["Logowanie", "Załóż konto"])
            tab_login = zakladki[0]    
            tab_register = zakladki[1]
        
        # --- ZAKŁADKA LOGOWANIA ---
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
        
        # --- ZAKŁADKA REJESTRACJI ---
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
                                    
                                    try:
                                        fire_db.collection('trenerzy').document(new_uid).set({
                                            'email': reg_email,
                                            'status': 'oczekujący',
                                            'data_rejestracji': firestore.SERVER_TIMESTAMP
                                        })
                                        
                                        # 2. Bezpieczne pobranie Discord Webhooka
                                        discord_url = get_env_or_secret("DISCORD_WEBHOOK")
                                        if discord_url:
                                            link_zatwierdz = f"{ADMIN_WEBHOOK_URL}?uid={new_uid}&action=approve&key={ADMIN_SECRET}"
                                            link_odrzuc = f"{ADMIN_WEBHOOK_URL}?uid={new_uid}&action=reject&key={ADMIN_SECRET}"

                                            wiadomosc = (
                                                f"🔔 **Nowa Rejestracja w CoachPlus!**\n"
                                                f"📧 Trener: `{reg_email}`\n"
                                                f"🔑 UID: `{new_uid}`\n\n"
                                                f"✅ [ZATWIERDŹ KONTO]({link_zatwierdz})\n"
                                                f"❌ [ODRZUĆ KONTO]({link_odrzuc})"
                                            )
                                            requests.post(discord_url, json={"content": wiadomosc})

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