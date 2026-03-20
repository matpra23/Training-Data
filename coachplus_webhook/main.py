import functions_framework
from flask import jsonify
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import time

if not firebase_admin._apps:
    firebase_admin.initialize_app()
db = firestore.client()

VERIFY_TOKEN = "COACHPLUS_TAJNY_TOKEN_123"
CLIENT_ID = "201249"
CLIENT_SECRET = "274d854d0a6eb35e9cfd4cad7da1b830fec2fff3"

def pobierz_aktywny_token(athlete_id):
    """Szuka zawodnika w bazie i odświeża token Stravy, jeśli wygasł."""
    zawodnicy_ref = db.collection('zawodnicy-v2').where('athlete_id', '==', athlete_id).limit(1).get()
    
    if not zawodnicy_ref:
        print(f"Nie znaleziono zawodnika o ID {athlete_id} w bazie.")
        return None, None
    
    doc = zawodnicy_ref[0]
    dane = doc.to_dict()
    expires_at = dane.get('expires_at', 0)
    
    if time.time() > expires_at:
        print("Token wygasł, odświeżam...")
        res = requests.post(
            "https://www.strava.com/api/v3/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": dane.get('refresh_token')
            }
        )
        if res.status_code == 200:
            nowe_tokeny = res.json()
            doc.reference.update({
                'access_token': nowe_tokeny['access_token'],
                'refresh_token': nowe_tokeny['refresh_token'],
                'expires_at': nowe_tokeny['expires_at']
            })
            return nowe_tokeny['access_token'], doc.reference
        else:
            print("Błąd odświeżania tokenu!")
            return None, None
            
    return dane.get('access_token'), doc.reference


@functions_framework.http
def strava_webhook(request):
    """Główna funkcja nasłuchująca."""
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return jsonify({"hub.challenge": challenge}), 200
        return "Forbidden", 403

    elif request.method == 'POST':
        data = request.get_json()
        print(f"Otrzymano ping ze Stravy: {data}")
        
        if data.get('object_type') == 'activity':
            athlete_id = data.get('owner_id')
            activity_id = data.get('object_id')
            aspect_type = data.get('aspect_type')
            
            # --- SCENARIUSZ 1: DODANIE TRENINGU ---
            if aspect_type == 'create':
                
                # ==========================================
                # 🛡️ BRAMKARZ (IDEMPOTENCY CHECK)
                # ==========================================
                zawodnicy_ref = db.collection('zawodnicy-v2').where('athlete_id', '==', athlete_id).limit(1).get()
                if zawodnicy_ref:
                    user_ref = zawodnicy_ref[0].reference
                    trening_ref = user_ref.collection('historia_treningow').document(str(activity_id))
                    
                    if trening_ref.get().exists:
                        print(f"🛡️ BRAMKARZ: Trening {activity_id} już istnieje w bazie! Ignoruję duplikat i wysyłam OK do Stravy.")
                        return "EVENT_RECEIVED", 200 # Natychmiastowe odcięcie połączenia, co uspokaja Stravę
                        
                    # Jeśli treningu nie ma, lecimy z pobieraniem tokenów i danych
                    token, _ = pobierz_aktywny_token(athlete_id)
                    if token:
                        print(f"Pobieranie pełnych danych treningu {activity_id}...")
                        headers = {'Authorization': f'Bearer {token}'}
                        response = requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers)
                        
                        if response.status_code == 200:
                            activity_data = response.json()
                            
                            if activity_data.get('has_heartrate'):
                                res_zones = requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}/zones', headers=headers)
                                if res_zones.status_code == 200:
                                    activity_data['zones'] = res_zones.json()
                            
                            # Zapis do Firebase
                            user_ref.collection('historia_treningow').document(str(activity_id)).set(activity_data)
                            print(f"SUKCES! Trening {activity_id} (ze strefami) wylądował w Firebase!")
                    
            # --- SCENARIUSZ 2: USUNIĘCIE TRENINGU ---
            elif aspect_type == 'delete':
                print(f"Otrzymano prośbę o usunięcie treningu {activity_id}...")
                zawodnicy_ref = db.collection('zawodnicy-v2').where('athlete_id', '==', athlete_id).limit(1).get()
                
                if zawodnicy_ref:
                    user_ref = zawodnicy_ref[0].reference
                    user_ref.collection('historia_treningow').document(str(activity_id)).delete()
                    print(f"SUKCES! Trening {activity_id} skasowany! 🗑️")

            # --- SCENARIUSZ 3: (ZMIANA NAZWY) ---
            elif aspect_type == 'update':
                updates = data.get('updates', {})
                
                if 'title' in updates:
                    nowa_nazwa = updates['title']
                    print(f"Trening {activity_id} zmienia nazwę na: {nowa_nazwa}")
                    
                    zawodnicy_ref = db.collection('zawodnicy-v2').where('athlete_id', '==', athlete_id).limit(1).get()
                    
                    if zawodnicy_ref:
                        user_ref = zawodnicy_ref[0].reference
                        trening_ref = user_ref.collection('historia_treningow').document(str(activity_id))
                        
                        if trening_ref.get().exists:
                            trening_ref.update({'name': nowa_nazwa})
                            print(f"SUKCES! Nazwa treningu zaktualizowana w Firebase!")
                        else:
                            print("Trening nie istnieje jeszcze w bazie (może został dodany przed podpięciem apki).")

        # Zawsze musimy odpowiedzieć 200 OK
        return "EVENT_RECEIVED", 200

    return "Method not allowed", 405