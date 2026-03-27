import streamlit as st
import pandas as pd
import plotly.express as px
import time
import requests
from stravalib.client import Client

from database import load_db, save_db, fire_db
from strava_services import parse_token_response
from config import get_env_or_secret # <-- Nasz bezpieczny włącznik

@st.dialog("Szczegóły Treningu", width="large")
def pokaz_analize(trening_id, zawodnik_imie):
    with st.spinner("Ładowanie analizy..."):
        try:
            doc_ref = fire_db.collection('podopieczni').document(zawodnik_imie).collection('historia_treningow').document(str(trening_id))
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

def render_analysis_view():
    db = load_db()
    
    if not db:
        st.info("Baza jest pusta. Przejdź do zakładki 'Dodaj Zawodnika', aby kogoś dodać.")
        return

    imiona = list(db.keys())
    wybrany_imie = st.selectbox("Wybierz podopiecznego:", imiona)
    
    if wybrany_imie and wybrany_imie in db:
        zawodnik_data = db[wybrany_imie]
        
        with st.expander("⚙️ Zarządzanie zawodnikiem"):
            st.warning(f"Czy na pewno chcesz usunąć zawodnika **{wybrany_imie}**? Usunięcie z bazy jest nieodwracalne.")
            if st.button(f"Ostatecznie usuń: {wybrany_imie}", type="primary"):
                with st.spinner("Usuwam historię treningów i czyszczę bazę... 🧹"):
                    treningi_ref = fire_db.collection('podopieczni').document(wybrany_imie).collection('historia_treningow')
                    treningi_docs = treningi_ref.stream()
                    
                    licznik = 0
                    for doc in treningi_docs:
                        doc.reference.delete()
                        licznik += 1
                        
                    fire_db.collection('podopieczni').document(wybrany_imie).delete()
                
                # ZMIANA: Bezpieczne pobieranie klucza Discord
                discord_url = get_env_or_secret("DISCORD_WEBHOOK")
                if discord_url:
                    wiadomosc_usuniecie = f"🗑️ **Zawodnik Usunięty!** (Skasowano {licznik} treningów oraz profil: **{wybrany_imie}**)"
                    requests.post(discord_url, json={"content": wiadomosc_usuniecie})
                    
                st.success(f"Pomyślnie usunięto zawodnika i wyczyszczono jego {licznik} treningów z bazy!")
                time.sleep(2) 
                st.rerun()
        
        client = Client()
        
        if time.time() > zawodnik_data['expires_at']:
            try:
                # ZMIANA: Bezpieczne pobieranie kluczy Strava
                client_id = get_env_or_secret("MY_CLIENT_ID")
                client_secret = get_env_or_secret("MY_CLIENT_SECRET")
                
                if client_id and client_secret:
                    refresh_response = client.refresh_access_token(
                        client_id=client_id,
                        client_secret=client_secret,
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
                    treningi_ref = fire_db.collection('podopieczni').document(wybrany_imie).collection('historia_treningow')
                    docs = treningi_ref.stream()
                    
                    data = []
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
                                    "Czas (min)": None 
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
                            
                            st.write("---")
                            st.subheader("Analiza stref tętna")

                            if sum(hr_zones_aggregated.values()) > 0:
                                df_zones = pd.DataFrame({
                                    "Strefa": list(hr_zones_aggregated.keys()),
                                    "Czas (min)": [int(round(v / 60)) for v in hr_zones_aggregated.values()]
                                })
                                
                                kolory_stref = {
                                    "Z1 (Regeneracja)": "#b4b4b8",
                                    "Z2 (Wytrzymałość)": "#4bb8ff",
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
                                st.info("Brak danych o strefach tętna w wybranym okresie.")
                    else:
                        st.warning("Brak treningów w tym okresie.")
                except Exception as e:
                    st.error(f"Wystąpił błąd: {e}")