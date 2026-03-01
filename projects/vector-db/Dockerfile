FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

LABEL io.modelcontextprotocol.server.name="io.github.kroq86/vector-db-mcp"

ARG PREWARM_EMBEDDINGS=0

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EMBEDDING_PROVIDER=fastembed
ENV EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
ENV EMBEDDING_CACHE_DIR=/models/fastembed
ENV HF_HOME=/models/huggingface
ENV XDG_CACHE_HOME=/models/xdg
ENV USE_ASM=1
ENV VECTOR_DB_PATH=/data/vectors.duckdb

RUN apt-get update && \
    apt-get install -y --no-install-recommends fasm gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data /models/fastembed /models/huggingface /models/xdg

COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
RUN if [ "$PREWARM_EMBEDDINGS" = "1" ]; then \
        python -c "from fastembed import TextEmbedding; list(TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/models/fastembed').embed(['warmup']))"; \
    fi

COPY dot_product.asm ./
COPY wrapper.c ./
RUN fasm dot_product.asm dot_product.o && \
    gcc -c -fPIC wrapper.c -o wrapper.o && \
    gcc -shared -fPIC -o dot_product.so dot_product.o wrapper.o

COPY duckdb_vec.py ./
COPY mcp_vector_server.py ./

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)); raise SystemExit(0 if data.get('ready') else 1)"

VOLUME ["/data", "/models"]

CMD ["python", "mcp_vector_server.py"]
