ARG PYTHON_VERSION=3.8
FROM python:${PYTHON_VERSION}-slim AS build

# Set a default project name if not provided
ARG PROJECT_NAME
ENV PROJECT_NAME=${PROJECT_NAME}

# Install project
WORKDIR /usr/src/app
COPY README.md pyproject.toml requirements.lock .
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock

# Copy project
COPY $PROJECT_NAME $PROJECT_NAME

# Save version (commit ID) into a file
RUN echo ${VERSION} > ./VERSION

# Create entrypoint script
RUN echo '#!/bin/sh\nexec python -m "'$PROJECT_NAME'"' > entrypoint.sh && \
    chmod +x entrypoint.sh

# Run as non-root
RUN addgroup --gid 1000 $PROJECT_NAME && useradd --gid 1000 -M --uid 1000 $PROJECT_NAME

USER $PROJECT_NAME
ENTRYPOINT ["./entrypoint.sh"]
