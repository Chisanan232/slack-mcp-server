# Use Python 3.13 as base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY . .

# Create a virtual environment and install dependencies using uv
RUN uv venv
RUN . .venv/bin/activate && uv pip install -e .
RUN . .venv/bin/activate && uv pip install -e --group=dev

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.venv/bin:$PATH"

# Expose port (adjust if your application uses a different port)
EXPOSE 8000

# Set the entry point
CMD ["uv", "run", "slack-mcp-server", "--transport", "sse"]
