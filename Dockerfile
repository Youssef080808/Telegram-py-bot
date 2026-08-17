# Start from an existing image
FROM python:3.11-slim 

# Creates a folder /app and makes it the current directory
WORKDIR /app 

# Copies file (dependencies)
COPY requirements.txt .

# To download the dependencies in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt 

# Copies everything else in project folder into image
COPY . . 

# Creates a folder /data and sets the environment varibale DATA_DIR to that folder
RUN mkdir -p /data
ENV DATA_DIR=/data

# Saves the command to run when someone starts a container from this image
CMD ["python3", "bot.py"]







