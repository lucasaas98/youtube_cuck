#Download Python from DockerHub and use it
FROM python:3.8-slim-buster

#Set the working directory in the Docker container
WORKDIR /code

#Copy the dependencies file to the working directory
COPY requirements.txt .

#Install the dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

#Plus FFMPEG for youtube-dl
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#Copy the Flask app code to the working directory
COPY . .

EXPOSE 5020

#Run the container
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5020", "ParseAndConfuse", "--timeout", "300"]
