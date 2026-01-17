FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .
COPY README.md .

# Copy source code
COPY src/ src/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
# Note: simulated_sans_data.csv is bundled inside the package at src/sans_webapp/data/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the Streamlit app using the package entry point
CMD ["streamlit", "run", "src/sans_webapp/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
