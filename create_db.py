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


print("Table created successfully")

conn.close()