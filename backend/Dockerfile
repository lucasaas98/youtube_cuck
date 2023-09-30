#Download Python from DockerHub and use it
FROM python:3-alpine

#Set the working directory in the Docker container
WORKDIR /code

#Copy the dependencies file to the working directory
COPY requirements.txt .

#Install the dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

#Plus FFMPEG for youtube-dl
RUN apk update \
    && apk add ffmpeg 

#Copy the Flask app code to the working directory
COPY . .

EXPOSE 5020

#Run the container
CMD uvicorn --host 0.0.0.0 --port 5020 backend:app
