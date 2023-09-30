# youtube_cuck

This program is designed to download videos from Youtube based on the RSS feed provided by Youtube themselves.

### Specifications
The program is designed with microsservices in mind.
This is a **FastAPI** project and **yt-dlp** is used to proceed with the download. All the important data is stored in a **MySQL** database. **NGINX** is being used as a file server for the frontend. 

### Requirements
You will need to have **Docker** and **docker compose** .

To install **Docker** follow the instructions [here](https://docs.docker.com/engine/install/).

To install **docker compose** after installing Docker follow the instructions [here](https://docs.docker.com/compose/install/). 


### Starting
Start by making sure the **docker-compose** files look good for you. To run the production version we will map folders to volumes and currently, they are the mappings from my server. Yours will surely be different. 

To run the program you will need to use the **make** file!

1. Get the deps

```make deps```

2. Running the DB and migrating

```make run-prod-db```

3. You can now build the backend, the frontend and the nginx images

```make build-prod```

4. You can now run everything

```make run-prod```

You should 100% take a look at the **Makefile** to see all the possible commands.

### Customization
You can add new channels by using the **Add Channel** button right in the frontend. You can also manually modify the subscription_manager file. 

Development is also easy if you want to customize anything else, just check the dev part of the **Makefile**


### How it works
When you enter the interface for the first time the frontend will tell the backend that it should look for new videos. 

If there are new videos to download the backend will download them to the persistent volume that is created. 

These videos will then be accessible to the frontend via the NGINX server. 

For each channel multiple video urls will be returned. Only the videos more recent than a certain date threshold (30 days, currently) are downloaded. 

To keep the size of the folders smaller, videos older than 10 days are automatically removed. 

All these values can be modified by changing the values in **youtube_cuck/backend/backend/constants.py**

### The idea
This was a quick and dirty python project that is proving to be very useful. 
The best part for me is the fact that the load times are absolutelly phenomenal, which makes sense since everything is found locally and there are no external libraries in the HTML/JS files.

Now that the development and production environments are pretty well defined it's easier than ever to add new features.

### What is to come
Currently working on: 
- Playlist download, creation and edition;
- System that downloads the videos in a lower quality thus saving space. Useful for videos where the audio is the major component.
