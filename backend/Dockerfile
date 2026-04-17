FROM python:3.11-slim

# System dependencies for WeasyPrint (Pango, Cairo, GDK-PixBuf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Place code at /workspace/backend so "backend.app.*" imports resolve correctly
WORKDIR /workspace

COPY requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . ./backend/

# alembic.ini must be run from the backend directory
WORKDIR /workspace/backend

ENV PYTHONPATH=/workspace

CMD ["bash", "start.sh"]
