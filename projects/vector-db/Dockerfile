FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends fasm gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt mcp

COPY dot_product.asm ./
RUN fasm dot_product.asm dot_product.o && \
    gcc -shared -fPIC -o dot_product.so dot_product.o

COPY duckdb_vec.py ./
COPY mcp_vector_server.py ./

CMD ["python", "mcp_vector_server.py"]
