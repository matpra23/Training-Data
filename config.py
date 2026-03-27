import os
import streamlit as st

def get_env_or_secret(key_name):
    """Leniwe pobieranie kluczy: Najpierw Cloud Run, potem lokalny plik."""
    if key_name in os.environ:
        return os.environ[key_name]
    
    try:
        return st.secrets[key_name]
    except Exception:
        return None