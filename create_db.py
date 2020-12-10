import sqlite3

conn = sqlite3.connect('yt_cuck.db')



def create_videos_table():
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
    print("Table downloaded_videos created successfully")

def create_json_table():
    conn.execute('''
        CREATE TABLE 'json_data' (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rss_feed_json TEXT
        );
    ''')
    print("Table json_data created successfully")

def create_video_flag_table():
    conn.execute('''
        CREATE TABLE 'video_flag' (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag INTEGER
        );
    ''')
    print("Table video_flag created successfully")

def create_rss_table():
    conn.execute('''
        CREATE TABLE 'rss_feed_date' (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_human VARCHAR(1000)
        );
    ''')
    print("Table rss_feed_date created successfully")


def create_tables():
    create_rss_table()
    create_videos_table()
    create_json_table()
    create_video_flag_table()
    print("All tables created.")

def close_conn():
    conn.close()

if __name__ == "__main__":
    #create_tables()
    #create_videos_table()
    create_rss_table()
    create_json_table()
    create_video_flag_table()
    close_conn()
