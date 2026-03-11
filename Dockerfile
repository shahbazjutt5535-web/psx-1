FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Patch the tvDatafeed library during build
RUN sed -i '/input(/d' /usr/local/lib/python3.11/site-packages/tvDatafeed/main.py

COPY . .

CMD ["python", "bot.py"]
