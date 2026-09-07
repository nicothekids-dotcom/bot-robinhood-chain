FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# watchlist.db akan dibuat otomatis di sini saat bot pertama kali jalan
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/watchlist.db

CMD ["python", "bot.py"]
