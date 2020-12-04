import sqlite3

conn = sqlite3.connect('yt_cuck.db')

conn.execute('''
    CREATE TABLE 'downloaded_videos' (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vid_url VARCHAR(1000) UNIQUE,
        thumb_url VARCHAR(1000),
        vid_path VARCHAR(1000),
        thumb_path VARCHAR(1000),
        pub_date INTEGER,
        pub_date_human VARCHAR(1000),
        rating REAL,
        title VARCHAR(1000),
        views INTEGER,
        description TEXT, 
        channel VARCHAR(1000)
    );
''')

# conn.execute('''
#     CREATE TABLE 'downloading' (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         vid_url VARCHAR(1000) UNIQUE
#     );
# ''')

print("Table created successfully")

conn.close()



#to insert use
# conn.execute("INSERT INTO downloaded_videos (vid_url,thumb_url,vid_path,thumb_path, pub_date) 
#   VALUES ('VID_URL', 'THUMB_URL', 'VID_PATH', 'THUMB_PATH', 'PUB_DATE')"


# to select
# cursor = conn.execute(
# "SELECT vid_url,thumb_url,vid_path,thumb_path from downloaded_videos where vid_url='VID_URL')