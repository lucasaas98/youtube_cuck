# Youtube Cuck

This program is designed to download videos from Youtube based on the RSS feed provided by Youtube themselves.


## Specifications
The program is designed with microsservices in mind.
This is a **FastAPI** project and **yt-dlp** is used to proceed with the download. All the important data is stored in a **MySQL** database. **NGINX** is being used as a file server for the frontend. 


## Requirements
You will need to have **Docker** and **docker compose** .

To install **Docker** follow the instructions [here](https://docs.docker.com/engine/install/).

To install **docker compose** after installing Docker follow the instructions [here](https://docs.docker.com/compose/install/). 


## Starting
_Start by making sure the **docker-compose** files look good for you. To run the production version we will map folders to volumes and currently, they are the mappings from my server. Yours will surely be different._

To run the program you will need to use the **make** file!

1. Get the deps

```sh
make deps
```

2. Running the DB and migrating

```sh
make run-prod-db
```

3. You can now build the backend, the frontend and the nginx images

```sh
make build-prod
```

4. You can now run everything

```sh
make run-prod
```

5. You might need this if you deal with livestreams a lot

```sh
make first
```

You should 100% take a look at the **Makefile** to see all the possible commands as well as the .env files to see all the possible environment variables.


## Customization
You can add new channels by using the **Add Channel** button right in the frontend. You can also manually modify the subscription_manager file. 

Development is also easy if you want to customize anything else, just check the dev part of the **Makefile** and the **.dev.env** files.


## How it works
1. When you enter the interface for the first time the frontend will tell the backend that it should look for new videos. 

2. If there are new videos to download the backend will download them to the persistent volume that is created. 

3. These videos will then be accessible to the frontend via the NGINX server. 

4. For each channel multiple video urls will be returned. Only the videos more recent than a certain date threshold (30 days, currently) are downloaded. 

5. To keep the size of the folders smaller, videos older than 10 days are automatically removed. 

4 and 5 values can be modified by changing the variables in **youtube_cuck/backend/backend/constants.py**


## The idea
This was a quick and dirty python project that is proving to be very useful. 
The best part for me is the fact that the load times are absolutelly phenomenal, which makes sense since everything is found locally and there are no external libraries in the HTML/JS files.

Now that the development and production environments are pretty well defined it's easier than ever to add new features.


### What is to come
Currently working on: 
- Playlist download, creation and edition;
- System that downloads the videos in a lower quality thus saving space. Useful for videos where the audio is the major component.
