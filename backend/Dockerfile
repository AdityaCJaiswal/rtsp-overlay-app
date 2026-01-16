FROM python:3.9-slim

WORKDIR /app

# 1. Install System Dependencies
# Fixed: Replaced 'libgl1-mesa-glx' with 'libgl1' and added 'libglib2.0-0'
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy App Code
COPY . .

CMD ["python", "app.py"]