# Use official Python image
FROM python:3.11-slim

# Install system dependencies needed for lxml and sqlite
RUN apt-get update && apt-get install -y gcc g++ libxml2-dev libxslt-dev

# Set up a new user named "user" with user ID 1000 for HuggingFace Permissions
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH \
	PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=1000 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy requirements first and install to leverage caching
COPY --chown=user requirements.txt $HOME/app/requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy heavy model files FIRST to ensure they are cached (since they rarely change)
COPY --chown=user qnai_model/ $HOME/app/qnai_model/

# Copy the remaining project files. Since the model is already in a previous layer,
# changes to app.py will no longer trigger a re-copy of the 1.2GB model.
COPY --chown=user . $HOME/app

# Create an upload folder if it doesn't exist
RUN mkdir -p static/uploads

# The database will be initialized at runtime in app.py

# Expose port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Command to run the application using Gunicorn (binding to port 7860)
CMD ["gunicorn", "-b", "0.0.0.0:7860", "--timeout", "600", "app:app"]
