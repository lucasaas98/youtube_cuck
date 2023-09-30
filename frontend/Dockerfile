#Download Python from DockerHub and use it
FROM python:3-alpine

#Set the working directory in the Docker container
WORKDIR /code

#Copy the dependencies file to the working directory
COPY requirements.txt .

#Install the dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip --no-cache-dir install -r requirements.txt

#Copy the Flask app code to the working directory
COPY . .

EXPOSE 5010

#Run the container
# CMD gunicorn --bind 0.0.0.0:5010 frontend:app --timeout 600
CMD uvicorn --host 0.0.0.0 --port 5010 frontend:app