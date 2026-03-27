import streamlit as st

def render_privacy_policy():
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