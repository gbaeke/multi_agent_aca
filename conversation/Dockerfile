# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Copy test script for debugging
COPY test_mcp_connection.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0"] 