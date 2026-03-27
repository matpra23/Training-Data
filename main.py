import streamlit as st
import os
from streamlit_option_menu import option_menu

# Importujemy nasze nowe moduły
from auth import check_password
from views.analysis import render_analysis_view
from views.builder import render_builder_view
from views.invite import render_invite_view
from views.privacy import render_privacy_policy
from views.success import render_success_view

# ==========================================
# ⚙️ KONFIGURACJA I SETUP
# ==========================================
st.set_page_config(page_title="CoachPlus Dashboard", page_icon="intmon.png", layout="wide")
os.environ["SILENCE_TOKEN_WARNINGS"] = "true"

st.logo("intmon.png", icon_image="intmon.png", link="https://coachplus.pl/")

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
    
    /* KARTY, EXPANDERY, FORMULARZE, BOCZNY PASEK */
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

    /* TYPOGRAFIA */
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

    /* PRZYCISKI PRIMARY */
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
    button[kind="primary"] *,
    div[data-testid="stFormSubmitButton"] button * {
        color: #000000 !important; 
        font-weight: 600 !important;
    }

    /* PRZYCISKI SECONDARY */
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

def render_footer():
    """Wyświetla stopkę na dole strony"""
    LINK_DO_POLITYKI = "https://app.coachplus.pl/?strona=prywatnosc"
    st.markdown(f"""
        <style>
        .footer {{
            position: fixed; left: 0; bottom: 0; width: 100%;
            background-color: #0a0a0c; color: #b4b4b8; text-align: center;
            padding: 12px; border-top: 1px solid rgba(255, 255, 255, 0.08);
            z-index: 9999; font-size: 13px;
        }}
        .footer a {{ color: #4bb8ff; text-decoration: none; font-weight: bold; transition: color 0.3s; }}
        .footer a:hover {{ color: #339ce3; text-decoration: underline; }}
        .block-container {{ padding-bottom: 60px; }}
        </style>
        <div class="footer">
            <p style="margin: 0;">© 2026 <b>IntMonDev</b>. All rights reserved. | Using Strava API | <a href="{LINK_DO_POLITYKI}" target="_blank">Polityka Prywatności</a></p>
        </div>
    """, unsafe_allow_html=True)

render_footer()

# ==========================================
# ROUTER (Zewnętrzne URL)
# ==========================================
query_params = st.query_params

if query_params.get("strona") == "prywatnosc":
    render_privacy_policy()
    st.stop()

if query_params.get("strona") == "sukces":
    code = query_params.get("code")
    trener_id = query_params.get("state")
    
    if code and trener_id:
        render_success_view(code, trener_id)
    else:
        st.warning("Nieprawidłowy link autoryzacyjny. Skontaktuj się ze swoim trenerem.")
        if st.button("Wróć do aplikacji"):
            st.query_params.clear() 
            st.rerun() 
            
    st.stop()

# ==========================================
# GŁÓWNA APLIKACJA (Zabezpieczona)
# ==========================================
if not check_password():
    st.stop()

st.title("Panel Trenera")

wybrana_zakladka = option_menu(
    menu_title=None,
    options=["Analiza treningów", "Utwórz trening", "Dodaj zawodnika"],
    icons=["graph-up", "calendar-check", "person-plus"],
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

# Przełączanie widoków
if wybrana_zakladka == "Analiza treningów":
    render_analysis_view()
elif wybrana_zakladka == "Utwórz trening":
    render_builder_view()
elif wybrana_zakladka == "Dodaj zawodnika":
    render_invite_view()