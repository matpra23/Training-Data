import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from config import get_env_or_secret

# Inicjalizacja bazy Firebase (Z mechanizmem Fallbacku)
if not firebase_admin._apps:
    try:
        firebase_json_str = get_env_or_secret("FIREBASE_JSON")
        if firebase_json_str:
            cert = json.loads(firebase_json_str)
        else:
            cert = dict(st.secrets["firebase"])
            
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Błąd inicjalizacji Firebase: {e}")

# Tworzymy globalnego klienta bazy danych
fire_db = firestore.client()

def load_db():
    db = {}
    try:
        obecny_trener_id = st.session_state.user_id
        docs = fire_db.collection('podopieczni').where('trener_id', '==', obecny_trener_id).stream()
        for doc in docs:
            db[doc.id] = doc.to_dict()
    except Exception as e:
        st.error(f"Błąd odczytu z bazy chmurowej: {e}")
    return db

def save_db(db, zmieniony_zawodnik=None):
    try:
        for imie, data in db.items():
            fire_db.collection('podopieczni').document(imie).set(data)
            
        discord_url = get_env_or_secret("DISCORD_WEBHOOK")
        if discord_url:
            wiadomosc = f"☁️ **Firebase Zaktualizowany!** (Dodano/odświeżono zawodnika: **{zmieniony_zawodnik}**)" if zmieniony_zawodnik else "☁️ **Firebase Zaktualizowany!** (Zapisano bazę)"
            requests.post(discord_url, json={"content": wiadomosc})
            
    except Exception as e:
        st.error(f"🚨 Błąd zapisu do bazy chmurowej: {e}")