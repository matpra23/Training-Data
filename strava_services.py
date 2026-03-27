# strava_services.py
def parse_token_response(response):
    """Bezpiecznie wyciąga tokeny i ID zawodnika."""
    if isinstance(response, tuple):
        response = response[0]
        
    athlete_id = None
        
    if isinstance(response, dict):
        athlete_data = response.get('athlete', {})
        if isinstance(athlete_data, dict):
            athlete_id = athlete_data.get('id')
            
        return {
            'access_token': response.get('access_token'),
            'refresh_token': response.get('refresh_token'),
            'expires_at': response.get('expires_at'),
            'athlete_id': athlete_id  
        }
    else:
        athlete_data = getattr(response, 'athlete', None)
        if athlete_data:
            if isinstance(athlete_data, dict):
                athlete_id = athlete_data.get('id')
            else:
                athlete_id = getattr(athlete_data, 'id', None)
                
        return {
            'access_token': getattr(response, 'access_token', None),
            'refresh_token': getattr(response, 'refresh_token', None),
            'expires_at': getattr(response, 'expires_at', None),
            'athlete_id': athlete_id  
        }

def extract_number(value, type_hint="number"):
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    if type_hint == "time":
        if hasattr(value, 'total_seconds'): return value.total_seconds()
        if hasattr(value, 'seconds'): return value.seconds
    if hasattr(value, 'magnitude'): return float(value.magnitude)
    if hasattr(value, 'num'): return float(value.num)
    try: return float(value)
    except: return 0.0