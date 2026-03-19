# 1. Baza: lekki Python 3.11
FROM python:3.11-slim

# 2. Tworzymy katalog roboczy w kontenerze
WORKDIR /app

# 3. Kopiujemy plik z wymaganiami i instalujemy biblioteki
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kopiujemy całą resztę Twojego kodu (WAŻNE: tu kopiuje się Twoje intmon.png)
COPY . .

# 5. THE DOCKER HACK: Włamanie do plików Streamlita
# -> Podmiana tytułu strony dla botów
RUN find /usr/local/lib/python* -name "index.html" -path "*/streamlit/static/index.html" -exec sed -i 's/<title>Streamlit<\/title>/<title>CoachPlus<\/title>/g' {} +
# -> Podmiana korony Streamlita na Twoje logo (nadpisujemy plik favicon.png)
RUN find /usr/local/lib/python* -type d -path "*/streamlit/static" -exec cp intmon.png {}/favicon.png \;

# 6. Wystawiamy port 8080 (standard dla Google Cloud Run)
EXPOSE 8080

# 7. Komenda uruchamiająca Streamlita
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]