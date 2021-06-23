#Download Python from DockerHub and use it
FROM python:3.8

#Set the working directory in the Docker container
WORKDIR /code

#Copy the dependencies file to the working directory
COPY requirements.txt .

#Install the dependencies
RUN pip install -r requirements.txt
#Plus FFMPEG for youtube-dl
RUN apt-get update
RUN apt-get -y install ffmpeg

#Copy the Flask app code to the working directory
COPY . .

EXPOSE 5020
#Run the container
CMD [ "python", "./ParseAndConfuse.py" ]