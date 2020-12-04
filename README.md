# youtube_cuck

This program is designed to download videos from Youtube based on the RSS feed provided by Youtube themselves.

###Specifications
This is a **flask** project and **youtube-dl** is used to proceed with the download. All the important data is stored in a **sqlite** database. The project uses Python 3.

###Requirements
There are a lot of requirements for this program to work. To install the python dependencies run
`pip install -r requirements.txt`
You will also need to install **youtube-dl**. Later I will use the youtube-dl python wrapper.

###How to run
First you need to create the sqlite database (only for the first time), to do that run:
`python create_db.py`
After that you can run:
`python main.py`
The interface will be available at __127.0.0.1:5000__. When you access this page for the first time after starting the program the RSS feed will be read and the recent videos (if there are any) will be downloaded, the schedule that checks every 10 minutes for newer videos will also be activated.

###How it works
__main.py__ is the script that controls the flask environment. In it you will find that the script __rss_info.py__ is called. This script is responsible for collecting the data related to the most recent videos produced by the channels specified in the file __subscription_manager__. For each channel multiple video urls will be returned. Only the videos more recent than a certain date threshold (2 days, currently) are downloaded. To keep the size of the folders smaller, videos older than 4 days are automatically removed. 

###The idea
This was a quick and dirty python project that is proving to be very useful. The best part for me is the fact that the load times are absolutelly phenomenal, which makes sense since everything is found locally and there are no external livraries in the HTML files.

###Known problems
- The RSS feed includes livestreams and I can't seem to find a way to use the flag is_live in the __--match-filter__ option from youtube-dl. 
- __Add channel__ and __Subscriptions__ tabs in the nav bar do nothing.