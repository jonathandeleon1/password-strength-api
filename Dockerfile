# Build stage. Dependencies are installed into an isolated virtualenv
# so the final image never carries build tooling or caches.
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Runtime stage. Patched base, no package manager, non-root user.
FROM python:3.13-slim

# Base images are rebuilt on a schedule, so even a freshly pulled tag can lag
# behind Debian security updates. Patching at build time closes that window.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user. Containers default to root, which means a
# container escape starts with root on the host.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv

# Strip pip and setuptools from the runtime image. This application never
# installs packages at run time, and shipping a package manager hands an
# attacker who lands in the container an easy way to pull down tooling.
RUN rm -rf /opt/venv/lib/python3.13/site-packages/pip* \
           /opt/venv/lib/python3.13/site-packages/setuptools* \
           /opt/venv/lib/python3.13/site-packages/pkg_resources \
           /opt/venv/bin/pip* \
           /usr/local/lib/python3.13/site-packages/pip* \
           /usr/local/lib/python3.13/site-packages/setuptools* \
           /usr/local/bin/pip*

WORKDIR /app
COPY app ./app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]