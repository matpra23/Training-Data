import streamlit as st
import time
import requests
from stravalib.client import Client
from database import fire_db
from strava_services import parse_token_response
from config import get_env_or_secret

def render_success_view(code, trener_id):
    st.markdown("### ⚙️ Trwa konfiguracja Twojego profilu...")
    with st.spinner("Łączenie ze Stravą i pobieranie historii treningów. Nie zamykaj okna..."):
        try:
            # Pobieranie zmiennych z chmury lub lokalnie
            client_id = get_env_or_secret("MY_CLIENT_ID")
            client_secret = get_env_or_secret("MY_CLIENT_SECRET")
            discord_url = get_env_or_secret("DISCORD_WEBHOOK")
            
            if not client_id or not client_secret:
                st.error("Brak konfiguracji API Stravy (Client ID / Secret).")
                st.stop()
            
            client = Client()
            # Używamy nowych zmiennych!
            token_response = client.exchange_code_for_token(
                client_id=client_id, 
                client_secret=client_secret, 
                code=code
            )
            nowe_dane = parse_token_response(token_response)
            
            headers = {'Authorization': f"Bearer {nowe_dane['access_token']}"}
            res = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
            
            if res.status_code == 200:
                dane_zawodnika = res.json()
                athlete_id = dane_zawodnika.get('id')
                imie = dane_zawodnika.get('firstname', 'Nieznany')
                nazwisko = dane_zawodnika.get('lastname', '')
                pelna_nazwa = f"{imie} {nazwisko}".strip()
            else:
                st.error("Nie udało się pobrać profilu ze Stravy.")
                st.stop()

            fire_db.collection('podopieczni').document(pelna_nazwa).set({
                'athlete_id': athlete_id, 
                'access_token': nowe_dane['access_token'],
                'refresh_token': nowe_dane['refresh_token'], 
                'expires_at': nowe_dane['expires_at'],
                'trener_id': trener_id 
            })

            res_activities = requests.get('https://www.strava.com/api/v3/athlete/activities', headers=headers, params={'after': int(time.time()) - (14 * 24 * 3600), 'per_page': 50})
            
            if res_activities.status_code == 200:
                activities_list = res_activities.json()
                user_ref = fire_db.collection('podopieczni').document(pelna_nazwa)
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
            
            # Fallback dla Discorda
            if discord_url:
                wiadomosc = f"🎉 **Nowy zawodnik autoryzowany!**\n**{pelna_nazwa}** właśnie dołączył do bazy i zgrał {zapisane_treningi} treningów!"
                requests.post(discord_url, json={"content": wiadomosc})

            st.success(f"Świetnie, {imie}! Twoje konto zostało połączone.")
            st.info("Twój trener ma już pełen dostęp do analizy Twoich treningów. Możesz bezpiecznie zamknąć tę stronę.")

        except Exception as e:
            st.error(f"Wystąpił błąd podczas autoryzacji: {e}")

    st.write("---")
    if st.button("Wróć do aplikacji (dla trenera)"):
        st.query_params.clear() 
        st.rerun()