import functions_framework
from flask import request
import firebase_admin
from firebase_admin import credentials, firestore

# Inicjalizacja bazy
if not firebase_admin._apps:
    firebase_admin.initialize_app()
db = firestore.client()

ADMIN_SECRET = "CoachPlus_Tajny_Klucz_999"

@functions_framework.http
def admin_action(request):
    """Funkcja odbierająca kliknięcia z Discorda"""
    
    # 🛑 WYKRYWACZ BOTÓW (Rozwiązanie problemu autozatwierdzania)
    user_agent = request.headers.get('User-Agent', '').lower()
    if 'discordbot' in user_agent or 'bot' in user_agent:
        return "Ignoruję automatyczne kliknięcie bota podglądu.", 200

    uid = request.args.get('uid')
    action = request.args.get('action')
    key = request.args.get('key')

    # Zabezpieczenie przed intruzami
    if key != ADMIN_SECRET:
        return "Brak dostępu. Błędny klucz weryfikacyjny.", 403
    
    if not uid or not action:
        return "Błąd: Brak parametrów UID lub akcji.", 400

    try:
        doc_ref = db.collection('trenerzy').document(uid)
        
        if not doc_ref.get().exists:
            return f"Błąd: Nie znaleziono trenera o UID {uid} w bazie.", 404

        if action == 'approve':
            doc_ref.update({'status': 'zatwierdzony'})
            return f"<h1>✅ SUKCES!</h1><p>Trener (UID: {uid}) został ZATWIERDZONY i może się logować.</p>", 200
            
        elif action == 'reject':
            doc_ref.update({'status': 'odrzucony'})
            return f"<h1>❌ ODRZUCONO</h1><p>Trener (UID: {uid}) został ODRZUCONY.</p>", 200
            
        else:
            return "Nieznana akcja.", 400
            
    except Exception as e:
        return f"Wystąpił błąd bazy danych: {e}", 500