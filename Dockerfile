# Use official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies needed for lxml and sqlite
RUN apt-get update && apt-get install -y gcc g++ libxml2-dev libxslt-dev

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Initialize the database
RUN python init_db.py

# Create an upload folder if it doesn't exist
RUN mkdir -p static/uploads

# Expose port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Command to run the application using Gunicorn (binding to port 7860)
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
