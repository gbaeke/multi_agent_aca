FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files and config folders
COPY *.py ./

# Run the main.py file
CMD ["python", "main.py"] 