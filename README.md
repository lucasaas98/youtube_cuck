# youtube_cuck

This program is designed to download videos from Youtube based on the RSS feed provided by Youtube themselves.

### Specifications
The program is now designed with microsservices in mind.
This is a **Flask** project and **youtube-dl** is used to proceed with the download. All the important data is stored in a **MySQL** database. **NGINX** is being used as a file server for the frontend. 

### Requirements
You will need to have **Docker** or **Docker** with **Minikube** installed.
To install **Docker** follow the instructions [here](https://docs.docker.com/engine/install/).
To install **minikube** after installing Docker follow the instructions [here](https://minikube.sigs.k8s.io/docs/start/). You might also need to install **kubectl** and in the Minikube website there are some instructions on how to do that.


### How to run
To run the program all you need to do is run the deployment script:

`./start_deployment.sh`

You can check whether the pods are ready with:

`minikube dashboard`

The interface can be obtained with the command:

`minikube service yt-cuck-fronted`
or
`minikube service yt-cuck-fronted --url=true`

if you only need the URL.

### How it works
When you enter the interface for the first time the frontend will tell the backend that it should look for new videos. 

If there are new videos to download the backend will download them to the persistent volume that is created. 

These videos will then be accessible to the frontend via the NGINX server. 

For each channel multiple video urls will be returned. Only the videos more recent than a certain date threshold (2 days, currently) are downloaded. 

To keep the size of the folders smaller, videos older than 4 days are automatically removed. 

### The idea
This was a quick and dirty python project that is proving to be very useful. The best part for me is the fact that the load times are absolutelly phenomenal, which makes sense since everything is found locally and there are no external livraries in the HTML files.

Now that the kubernetes environment is ready it is also very easy to setup in new machines. The only thing that is really needed is to transfer my real **subscription_manager** file to the **nginx_server** folder and I'm golden.

### What is to come
Currently working on: 
- Playlist download, creation and edition;
- System that downloads the videos in a lower quality thus saving space. Useful for videos where the audio is the major component.
