FROM python:3.11

WORKDIR /app

COPY requirements.txt .

# Install PyTorch CPU version without hash verification
RUN pip install --no-cache-dir --timeout=300 --trusted-host download.pytorch.org \
    numpy==1.24.3

RUN pip install --no-cache-dir --timeout=300 --trusted-host download.pytorch.org \
    torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# Install other requirements
RUN pip install --no-cache-dir --timeout=300 -r requirements.txt

# Install whisper (without hash verification to avoid hash mismatch errors)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --no-deps openai-whisper ffmpeg-python \
 && pip install --no-cache-dir tiktoken tqdm more-itertools numba llvmlite

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]