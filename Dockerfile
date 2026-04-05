# Use the official Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Hugging Face Spaces runs as user 1000)
RUN useradd -m -u 1000 user
USER user

# Copy the application code using the new user permissions
COPY --chown=user . /app

# Ensure the SQLite data directory exists and is writable
RUN mkdir -p /app/data

# Hugging Face Spaces exposes port 7860 natively
ENV PORT=7860
EXPOSE 7860

# Start the FastAPI Uvicorn server on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
