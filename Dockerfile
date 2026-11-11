FROM python:3.12-slim
WORKDIR /app
COPY src/ src/
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1
RUN useradd --create-home app && mkdir -p /app/diagnostics && chown app /app/diagnostics
USER app
CMD ["python", "-m", "connector", "run"]
