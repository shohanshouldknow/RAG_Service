FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/docusense/.cache/huggingface

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 docusense \
    && mkdir -p /app/storage/chroma "${HF_HOME}" \
    && chown -R docusense:docusense /app /home/docusense

COPY --chown=docusense:docusense app ./app
COPY --chown=docusense:docusense scripts ./scripts
COPY --chown=docusense:docusense data ./data

USER docusense

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
