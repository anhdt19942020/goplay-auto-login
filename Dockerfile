FROM python:3.13-slim

# Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg2 xvfb \
    fonts-liberation fonts-noto-cjk \
    libnss3 libxss1 libasound2t64 libatk-bridge2.0-0 \
    libgtk-3-0 libgbm1 libdrm2 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libpango-1.0-0 libcairo2 libcups2 \
    libdbus-1-3 libatspi2.0-0 \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /usr/share/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DOCKER_ENV=1

EXPOSE 8000

CMD ["bash", "-c", "Xvfb :99 -screen 0 1280x720x24 -nolisten tcp & export DISPLAY=:99 && sleep 1 && exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"]
