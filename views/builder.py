import time
import datetime
import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from database import fire_db, firestore

# Słownik kolorów 
KOLORY_TRENINGOW = {
    "Bieganie": "#2e7b32",
    "Rower": "#d32f2f",
    "Basen": "#1565c0",
    "Siłownia": "#f57c00",
    "Regeneracja": "#757575",
    "Inne": "#b4b4b8"
}

# Hierarchia podkategorii
SUBKATEGORIE_TRENINGOW = {
    "Bieganie": ["Easy", "Interwały", "Tempo", "Threshold", "VO2max", "Beztlen", "Podbiegi", "Technika", "Długie wybieganie", "Regeneracja"],
    "Rower": ["Easy", "Interwały", "Tempo", "Threshold", "Technika", "Długa jazda", "Regeneracja"],
    "Basen": ["Rozpływanie (Easy)", "Drills (Technika)", "Interwały", "Long", "Regeneracja"],
    "Siłownia": ["Siła maksymalna", "Wytrzymałość siłowa", "Core", "Mobilność", "Ogólnorozwojowy"],
    "Regeneracja": ["Stretching", "Rolowanie", "Joga", "Spacer", "Całkowity rest"],
    "Inne": ["Brak"]
}

@st.dialog("Zaplanuj jednostkę")
def dodaj_trening_dialog(zawodnik_imie):
    st.markdown(f"Planujesz trening dla: **{zawodnik_imie}**")
    
    col1, col2 = st.columns(2)
    typ_treningu = col1.selectbox("Dyscyplina", list(KOLORY_TRENINGOW.keys()))
    podkategoria = col2.selectbox("Typ jednostki", SUBKATEGORIE_TRENINGOW.get(typ_treningu, ["Brak"]))
    
    st.markdown("---")
    c_data, c_godz, c_cel, c_wart = st.columns([1, 1, 1.2, 1])
    data_treningu = c_data.date_input("Data", pd.to_datetime("today"))
    godzina_treningu = c_godz.time_input("Godzina", value=datetime.time(8, 0))
    rodzaj_celu = c_cel.selectbox("Cel jednostki", ["Czas (min)", "Dystans (km)", "Tylko opis"])
    
    wartosc_celu = 0.0
    if rodzaj_celu == "Czas (min)":
        wartosc_celu = c_wart.number_input("Wartość (min)", min_value=5, max_value=600, step=5, value=60)
    elif rodzaj_celu == "Dystans (km)":
        wartosc_celu = c_wart.number_input("Wartość (km)", min_value=0.5, max_value=200.0, step=0.5, value=10.0)
    
    st.markdown("---")
    notatka = st.text_area("Notatka dla zawodnika", placeholder="Szczegóły wykonania treningu...")
    rpe = st.slider("Zakładane RPE (Skala zmęczenia 1-10)", min_value=1, max_value=10, value=5, step=1)
    
    if st.button("Zapisz trening", type="primary", use_container_width=True):
        with st.spinner("Zapisuję w chmurze..."):
            try:
                # Łączymy datę i godzinę w poprawny string ISO8601 (potrzebne do sortowania!)
                data_iso = f"{data_treningu}T{godzina_treningu.strftime('%H:%M:%S')}"
                
                ref_plany = fire_db.collection('podopieczni').document(zawodnik_imie).collection('zaplanowane_treningi')
                
                nowy_trening = {
                    "typ_treningu": typ_treningu,
                    "podkategoria": podkategoria,
                    "data_treningu": data_iso, 
                    "rodzaj_celu": rodzaj_celu,
                    "wartosc_celu": float(wartosc_celu),
                    "notatka": notatka,
                    "rpe": rpe, 
                    "kolor": KOLORY_TRENINGOW.get(typ_treningu, "#b4b4b8"),
                    "status": "zaplanowany",
                    "stworzono": firestore.SERVER_TIMESTAMP
                }
                
                ref_plany.add(nowy_trening)
                st.success("Świetnie! Trening został zapisany.")
                time.sleep(1) 
                st.rerun() 
            except Exception as e:
                st.error(f"Błąd podczas zapisywania treningu: {e}")

@st.dialog("Edytuj lub usuń trening")
def edytuj_trening_dialog(zawodnik_imie, event_data):
    props = event_data["extendedProps"]
    db_id = props["db_id"]
    
    st.markdown(f"Edytujesz trening zawodnika: **{zawodnik_imie}**")
    
    col1, col2 = st.columns(2)
    lista_dyscyplin = list(KOLORY_TRENINGOW.keys())
    try: dyscyplina_idx = lista_dyscyplin.index(props.get("typ_treningu", "Bieganie"))
    except ValueError: dyscyplina_idx = 0
    typ_treningu = col1.selectbox("Dyscyplina", lista_dyscyplin, index=dyscyplina_idx, key="edit_type")
    
    podkategorie_lista = SUBKATEGORIE_TRENINGOW.get(typ_treningu, ["Brak"])
    try: podkategoria_idx = podkategorie_lista.index(props.get("podkategoria", ""))
    except ValueError: podkategoria_idx = 0
    podkategoria = col2.selectbox("Typ jednostki", podkategorie_lista, index=podkategoria_idx, key="edit_sub")
    
    st.markdown("---")
    
    # Odzyskiwanie daty i godziny
    stara_data_iso = event_data.get("start", "")
    try:
        dt_obj = pd.to_datetime(stara_data_iso)
        domyslna_data = dt_obj.date()
        domyslna_godzina = dt_obj.time()
    except:
        domyslna_data = pd.to_datetime("today").date()
        domyslna_godzina = datetime.time(8, 0)

    c_data, c_godz, c_cel, c_wart = st.columns([1, 1, 1.2, 1])
    data_treningu = c_data.date_input("Data", value=domyslna_data, key="edit_date")
    godzina_treningu = c_godz.time_input("Godzina", value=domyslna_godzina, key="edit_time")
    
    stary_rodzaj = props.get("rodzaj_celu", "Tylko opis")
    stara_wartosc = float(props.get("wartosc_celu", 0.0))
    lista_celow = ["Czas (min)", "Dystans (km)", "Tylko opis"]
    try: cel_idx = lista_celow.index(stary_rodzaj)
    except ValueError: cel_idx = 2
    
    rodzaj_celu = c_cel.selectbox("Cel jednostki", lista_celow, index=cel_idx, key="edit_cel")
    
    wartosc_celu = 0.0
    if rodzaj_celu == "Czas (min)":
        wartosc_celu = c_wart.number_input("Wartość (min)", min_value=5, max_value=600, step=5, value=int(stara_wartosc) if stara_wartosc > 0 else 60, key="edit_val_czas")
    elif rodzaj_celu == "Dystans (km)":
        wartosc_celu = c_wart.number_input("Wartość (km)", min_value=0.5, max_value=200.0, step=0.5, value=stara_wartosc if stara_wartosc > 0 else 10.0, key="edit_val_dyst")

    st.markdown("---")
    notatka = st.text_area("Notatka dla zawodnika", value=props.get("notatka", ""), key="edit_note")
    
    stare_rpe = int(props.get("rpe", 5))
    rpe = st.slider("Zakładane RPE (Skala zmęczenia 1-10)", min_value=1, max_value=10, value=stare_rpe, step=1, key="edit_rpe")
    
    st.write("---")
    c_zapisz, c_usun = st.columns(2)
    
    if c_zapisz.button("Zapisz zmiany", type="primary", use_container_width=True):
        with st.spinner("Aktualizowanie..."):
            nowa_data_iso = f"{data_treningu}T{godzina_treningu.strftime('%H:%M:%S')}"
            
            fire_db.collection('podopieczni').document(zawodnik_imie).collection('zaplanowane_treningi').document(db_id).update({
                "typ_treningu": typ_treningu,
                "podkategoria": podkategoria,
                "data_treningu": nowa_data_iso,
                "rodzaj_celu": rodzaj_celu,
                "wartosc_celu": float(wartosc_celu),
                "notatka": notatka,
                "rpe": rpe,
                "kolor": KOLORY_TRENINGOW.get(typ_treningu, "#b4b4b8")
            })
            st.success("Zaktualizowano trening!")
            time.sleep(1)
            st.rerun()
            
    if c_usun.button("🗑️ Usuń trening", type="secondary", use_container_width=True):
        with st.spinner("Usuwanie..."):
            fire_db.collection('podopieczni').document(zawodnik_imie).collection('zaplanowane_treningi').document(db_id).delete()
            st.success("Usunięto pomyślnie!")
            time.sleep(1)
            st.rerun()

def render_builder_view():
    from database import load_db 
    
    st.markdown("### Zaplanuj jednostki treningowe")
    
    db_kreator = load_db()
    if not db_kreator:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby móc układać plany.")
        return

    imiona_kreator = list(db_kreator.keys())
    wybrany_zawodnik_plan = st.selectbox("Wybierz podopiecznego:", imiona_kreator, key="kreator_wybor_zawodnika")
    
    st.divider()

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("➕ Dodaj trening", type="primary", use_container_width=True):
            dodaj_trening_dialog(wybrany_zawodnik_plan)

    st.write("")

    lista_eventow = []
    
    with st.spinner("Wczytywanie planu treningowego..."):
        try:
            plany_ref = fire_db.collection('podopieczni').document(wybrany_zawodnik_plan).collection('zaplanowane_treningi')
            docs = plany_ref.stream()
            
            for doc in docs:
                dane = doc.to_dict()
                
                typ = dane.get("typ_treningu", "Trening")
                podkat = dane.get("podkategoria", "")
                
                bazowy_tytul = f"{typ} - {podkat}" if podkat and podkat != "Brak" else typ
                
                rodzaj_celu = dane.get("rodzaj_celu", "")
                wartosc_celu = dane.get("wartosc_celu", 0.0)
                szczegoly_celu = ""
                
                if rodzaj_celu == "Czas (min)" and wartosc_celu > 0:
                    szczegoly_celu = f"⏱️ {int(wartosc_celu)} min"
                elif rodzaj_celu == "Dystans (km)" and wartosc_celu > 0:
                    szczegoly_celu = f"📏 {wartosc_celu} km"
                
                notatka = dane.get("notatka", "")
                rpe = dane.get("rpe", 0)
                
                widoczny_tytul = bazowy_tytul
                if szczegoly_celu:
                    widoczny_tytul += f"\n{szczegoly_celu}"
                if rpe > 0:
                    widoczny_tytul += f"\n⚡ RPE: {rpe}/10"
                if notatka:
                    widoczny_tytul += f"\n📝 {notatka}"
                
                lista_eventow.append({
                    "title": widoczny_tytul,
                    "start": dane.get("data_treningu", ""),
                    "color": dane.get("kolor", "#4bb8ff"),
                    "extendedProps": {
                        "db_id": doc.id,
                        "typ_treningu": typ,
                        "podkategoria": podkat,
                        "rodzaj_celu": rodzaj_celu,
                        "wartosc_celu": wartosc_celu,
                        "notatka": notatka,
                        "rpe": rpe,
                        "status": dane.get("status", "zaplanowany")
                    }
                })
        except Exception as e:
            st.error(f"Wystąpił błąd przy pobieraniu kalendarza: {e}")

    legenda_html = ""
    for sport, kolor in KOLORY_TRENINGOW.items():
        legenda_html += f"<span style='display:inline-block; margin-right: 15px;'><span style='display:inline-block; width:12px; height:12px; background-color:{kolor}; border-radius:50%; margin-right:5px; vertical-align:middle;'></span><span style='color:#b4b4b8; font-size:13px; vertical-align:middle;'>{sport}</span></span>"
    
    st.markdown(f"<div style='margin-bottom: 15px; padding: 10px; background-color: #0a0a0c; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;'>{legenda_html}</div>", unsafe_allow_html=True)

# --- KONFIGURACJA I RENDER KALENDARZA ---
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            # ZMIANA: Dodajemy listWeek - zbawienie dla telefonów!
            "right": "dayGridMonth,listWeek" 
        },
        "initialView": "dayGridMonth",
        "height": "auto", # ZMIANA: Zamiast sztywnego 650px, kalendarz sam dopasuje wysokość
        "locale": "pl",       
        "firstDay": 1,        
        "editable": False, 
        "displayEventTime": False, 
        "eventDisplay": "block",
        "views": {
            "dayGridMonth": {"dayHeaderFormat": {"weekday": "short"}}, # Krótsze nazwy dni na siatce
            "listWeek": {
                "buttonText": "Lista (Tel)", # Zmieniamy nazwę przycisku na zrozumiałą
                "noEventsText": "Brak zaplanowanych treningów w tym tygodniu."
            }
        }
    }

    try:
        cal_data = calendar(
            events=lista_eventow, 
            options=calendar_options, 
            custom_css="""
                .fc-event-title { white-space: pre-wrap !important; font-weight: 600; font-size: 13px; padding: 4px; line-height: 1.4; }
                .fc-toolbar-title { font-weight: bold; color: #f5f5f7; }
                .fc-button { background-color: #0a0a0c !important; border-color: rgba(255,255,255,0.08) !important; color: #f5f5f7 !important; text-transform: capitalize; }
                .fc-button-active { background-color: #4bb8ff !important; color: #000 !important; font-weight: bold !important; }
                .fc-theme-standard td, .fc-theme-standard th { border-color: rgba(255,255,255,0.08); }
                .fc-daygrid-day-number { color: #b4b4b8; text-decoration: none; }
                .fc-daygrid-day-number:hover { color: #4bb8ff; }
                .fc-day-today { background-color: rgba(75, 184, 255, 0.05) !important; }
                .fc-event { cursor: pointer; margin: 5px !important; } 
                
                /* ZMIANA: Specjalne stylowanie widoku listy */
                .fc-list-day-cushion { background-color: rgba(255,255,255,0.05) !important; color: #f5f5f7 !important; font-weight: bold; }
                .fc-list-event:hover td { background-color: rgba(75, 184, 255, 0.1) !important; }
                
                /* ZMIANA: Media Queries dla małych ekranów (Telefonów) */
                @media (max-width: 768px) {
                    .fc-toolbar { flex-direction: column; gap: 10px; }
                    .fc-toolbar-title { font-size: 1.2rem !important; }
                    .fc-button { padding: 4px 8px !important; font-size: 12px !important; }
                }
            """,
            key=f"kalendarz_{wybrany_zawodnik_plan}"
        )
        
        if cal_data is not None and cal_data.get("callback") == "eventClick":
            klikniety_event = cal_data["eventClick"]["event"]
            edytuj_trening_dialog(wybrany_zawodnik_plan, klikniety_event)
            
    except Exception as e:
        st.error(f"Błąd ładowania komponentu kalendarza: {e}")