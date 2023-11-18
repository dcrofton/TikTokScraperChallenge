FROM python:3.9-slim-buster

# Install Firefox and other dependencies
RUN apt-get update && apt-get install -y firefox-esr

# Install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install xvfb and xauth packages
RUN apt-get install -y xvfb xauth

# Copy Python script
COPY main.py .

# Run script with xvfb
CMD ["xvfb-run", "--server-args='-screen 0 1024x768x24'", "--auto-servernum", "python", "main.py"]