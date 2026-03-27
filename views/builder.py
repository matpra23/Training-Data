import streamlit as st
import pandas as pd

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

def render_builder_view():
    st.markdown("### Zaplanuj jednostki treningowe")
    st.markdown("##### Zakładka jest w trakcie rozbudowy")
    st.info("Logika kalendarza i dodawania treningów czeka na wdrożenie zapisu do bazy.")
    # Zostawiamy to miejsce przygotowane na dalszy rozwój (tutaj trafi kalendarz).