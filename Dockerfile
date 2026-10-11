FROM python:3.12.13-slim
WORKDIR /opt/womi
COPY requirements-eval.txt ./
RUN pip install --no-cache-dir -r requirements-eval.txt
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
RUN useradd --create-home --uid 10001 evaluator
USER evaluator
WORKDIR /work
ENTRYPOINT ["womi"]
