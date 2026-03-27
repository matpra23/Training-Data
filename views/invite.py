import streamlit as st
from stravalib.client import Client
from config import get_env_or_secret

def render_invite_view():
    st.header("Zaproś nowego podopiecznego")
    st.markdown("Wyślij zawodnikowi poniższy link. Gdy tylko autoryzuje połączenie ze Stravą, automatycznie pojawi się w Twoim panelu z wgraną historią treningów!")
    
    client_id = get_env_or_secret("MY_CLIENT_ID")
    
    if not client_id:
        st.error("Brak skonfigurowanego MY_CLIENT_ID.")
        return

    client = Client()
    
    # Przekazujemy ID trenera w parametrze state, używamy małej zmiennej client_id
    auth_url = client.authorization_url(
        client_id=client_id,
        redirect_uri='https://app.coachplus.pl/?strona=sukces',
        scope=['activity:read_all'],
        state=st.session_state.user_id 
    )
    
    st.code(auth_url)
    st.info("Nie musisz nic więcej klikać. System zrobi wszystko za Ciebie.")