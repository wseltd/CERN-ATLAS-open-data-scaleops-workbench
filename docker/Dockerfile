FROM python:3.11-slim

# Install system packages required by xrootd bindings.
# Combined into a single layer to keep image lean.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libssl-dev \
        libkrb5-dev \
        libfuse2 \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest first so Docker caches the pip-install layer
# independently of source changes.
COPY pyproject.toml ./

RUN pip install --no-cache-dir -e ".[test]"

# Copy source after pip install to preserve cache on code-only changes
COPY atlas_workbench/ ./atlas_workbench/
COPY fixtures/ ./fixtures/
COPY scripts/ ./scripts/

# Create non-root user and switch to it
RUN useradd --create-home atlas
USER atlas

EXPOSE 8000

CMD ["uvicorn", "atlas_workbench.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
