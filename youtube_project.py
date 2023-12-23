from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st

#Api key connection

def Api_connect():
    Api_Id="AIzaSyBuzR0uEWA72Ux2yaU79lKAcfuszeNtGpc"

    api_service_name="youtube"
    api_version="v3"

    youtube=build(api_service_name,api_version,developerKey=Api_Id)

    return youtube

youtube=Api_connect()

#get channel information
def get_channel_info(channel_id):
    request=youtube.channels().list(
                    part="snippet,ContentDetails,statistics",
                    id=channel_id
    )
    response=request.execute()

    for i in response['items']:
        data=dict(Channel_Name=i["snippet"]["title"],
                Channel_Id=i["id"],
                Subscribers=i['statistics']['subscriberCount'],
                Views=i["statistics"]["viewCount"],
                Total_Videos=i["statistics"]["videoCount"],
                Channel_Description=i["snippet"]["description"],
                Playlist_Id=i["contentDetails"]["relatedPlaylists"]["uploads"])
    return data


#get videos ids
def get_videos_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id,
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=Playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][0]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids


#get video information
def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,ContentDetails,statistics",
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    Video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    published_Dates=item['snippet']['publishedAt'],
                    Duration=item['contentDetails']['duration'],
                    Views=item['statistics'].get('viewCount'),
                    Likes=item['statistics'].get('likeCount'),
                    Comments=item['statistics'].get('commentCount'),
                    Favorite_Count=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_Status=item['contentDetails']['caption']
                    )
            video_data.append(data)
    
    return video_data

# get comment inforformation
def get_comment_info(video_ids):
    Comment_data=[]

    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                        Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        Comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                Comment_data.append(data)
    except:
        pass
    return Comment_data

#get playlist_details
def get_playlist_details(channel_id):
  next_page_token=None
  All_data=[]
  while True:
    request=youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token
    )
    response=request.execute()

    for item in response['items']:
        data=dict(Playlist_Id=item['id'],
                  Title=item['snippet']['title'],
                  Channel_Id=item['snippet']['channelId'],
                  Channel_Name=item['snippet']['channelTitle'],
                  PublishedAt=item['snippet']['publishedAt'],
                  Video_Count=item['contentDetails']['itemCount']) 
        All_data.append(data)

    next_page_token=response.get('nextPageToken')
    if next_page_token is None:
      break  
  return All_data

#mongo connection/uploading
client=pymongo.MongoClient("mongodb://localhost:27017/?readPreference=primary&ssl=false&directConnection=true")
db=client["Nitish_YouTube_data"]

def channel_details(channel_id):
    ch_details=get_channel_info(channel_id)
    pl_details=get_playlist_details(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)    
    com_details=get_comment_info(vi_ids)

    coll1=db["channel_details"]

    coll1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,
                      "video_information":vi_details,"comment_information":com_details})
    
    return "upload Succsssfully"

#table creation for channels,playlist,videos,comments into sql
def channels_table():

    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="nitish",
                        database="Nitish_YouTube_data",
                        port="5432")

    cursor=mydb.cursor()


    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists channels(Channel_Name varchar(100),
                                                            Channel_Id varchar(80) primary key,
                                                            Subscribers bigint,
                                                            Views bigint,
                                                            Total_Videos int,
                                                            Channel_Description text,
                                                            Playlist_Id varchar(80))'''
    cursor.execute(create_query)
    mydb.commit()
    
    ch_list=[]
    db=client["Nitish_YouTube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=pd.DataFrame(ch_list)

    for index,row in df.iterrows():
        insert_query='''insert into channels(Channel_Name,
                                            Channel_Id,
                                            Subscribers,
                                            Views,
                                            Total_Videos,
                                            Channel_Description,
                                            Playlist_Id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Subscribers'],
                row['Views'],
                row['Total_Videos'],
                row['Channel_Description'],
                row['Playlist_Id'])
        
        cursor.execute(insert_query,values)
        mydb.commit()          


#playlists
def playlist_table():
        mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="nitish",
                        database="Nitish_YouTube_data",
                        port="5432")

        cursor=mydb.cursor()


        drop_query='''drop table if exists playlists'''
        cursor.execute(drop_query)
        mydb.commit()

        create_query = '''CREATE TABLE IF NOT EXISTS playlists (
                    Playlist_Id VARCHAR(200) PRIMARY KEY,
                    Title VARCHAR(200),
                    Channel_Id VARCHAR(200),
                    Channel_Name VARCHAR(200),
                    PublishedAt TIMESTAMP,
                    Video_Count bigint
                )'''
        cursor.execute(create_query)
        mydb.commit()

        pl_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
                for i in range(len(pl_data["playlist_information"])):
                        pl_list.append(pl_data["playlist_information"][i])
        df1=pd.DataFrame(pl_list)

        for index,row in df1.iterrows():
                insert_query='''insert into playlists(Playlist_Id,
                                                Title,
                                                Channel_Id,
                                                Channel_Name,
                                                PublishedAt,
                                                Video_Count)
                                                
                                                values(%s,%s,%s,%s,%s,%s)'''
                
                values=(row['Playlist_Id'],
                        row['Title'],
                        row['Channel_Id'],
                        row['Channel_Name'],
                        row['PublishedAt'],
                        row['Video_Count'])
                
        cursor.execute(insert_query,values)
        mydb.commit()


#videos
def videos_table():
        mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="nitish",
                                database="Nitish_YouTube_data",
                                port="5432")

        cursor=mydb.cursor()


        drop_query='''drop table if exists videos'''
        cursor.execute(drop_query)
        mydb.commit()

        create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                        Channel_Id varchar(100),
                                                        Video_Id varchar(40) primary key,
                                                        Title varchar(150),
                                                        Tags text ,
                                                        Thumbnail varchar(250),
                                                        Description text,
                                                        published_Dates timestamp,
                                                        Duration interval,
                                                        Views bigint,
                                                        Likes int,
                                                        Comments int,
                                                        Favorite_Count int,
                                                        Definition varchar(20),
                                                        Caption_Status varchar(50) 
                                                        )'''
        cursor.execute(create_query)
        mydb.commit()
        vi_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for vi_data in coll1.find({},{"_id":0,"video_information":1}):
                for i in range(len(vi_data["video_information"])):
                        vi_list.append(vi_data["video_information"][i])
        df2=pd.DataFrame(vi_list)
        for index,row in df2.iterrows():
                        insert_query='''insert into videos(Channel_Name,
                                                        Channel_Id,
                                                        Video_Id,
                                                        Title,
                                                        Tags,
                                                        Thumbnail,
                                                        Description,
                                                        published_Dates,
                                                        Duration,
                                                        Views,
                                                        Likes,
                                                        Comments,
                                                        Favorite_Count,
                                                        Definition,
                                                        Caption_Status)
                                                        
                                                        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
                        
                        values=(row['Channel_Name'],
                                row['Channel_Id'],
                                row['Video_Id'],
                                row['Title'],
                                row['Tags'],
                                row['Thumbnail'],
                                row['Description'],
                                row['published_Dates'],
                                row['Duration'],
                                row['Views'],
                                row['Likes'],
                                row['Comments'],
                                row['Favorite_Count'],
                                row['Definition'],
                                row['Caption_Status']
                                )

                        cursor.execute(insert_query,values)
                        mydb.commit()

#comments
def comments_table():
        mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="nitish",
                        database="Nitish_YouTube_data",
                        port="5432")

        cursor=mydb.cursor()


        drop_query='''drop table if exists comments'''
        cursor.execute(drop_query)
        mydb.commit()

        create_query='''create table if not exists comments(Comment_Id varchar(100) primary key,
                                Video_Id varchar(50),
                                Comment_Text text,
                                Comment_Author varchar(150),
                                Comment_Published timestamp
                                )'''
        cursor.execute(create_query)
        mydb.commit()
        com_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for com_data in coll1.find({},{"_id":0,"comment_information":1}):
                for i in range(len(com_data["comment_information"])):
                        com_list.append(com_data["comment_information"][i])
        df3=pd.DataFrame(com_list)
        for index,row in df3.iterrows():
                        insert_query='''insert into comments(Comment_Id,
                                                                Video_Id,
                                                                Comment_Text,
                                                                Comment_Author,
                                                                Comment_Published)
                                                        
                                                        values(%s,%s,%s,%s,%s)'''
                        
                        values=(row['Comment_Id'],
                                row['Video_Id'],
                                row['Comment_Text'],
                                row['Comment_Author'],
                                row['Comment_Published']
                                )

                        cursor.execute(insert_query,values)
                        mydb.commit()


def tables():
    channels_table()
    playlist_table()
    videos_table()
    comments_table()

    return "table created"

def show_channels_table():
    ch_list=[]
    db=client["Nitish_YouTube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)

    return df

def show_playlists_table():
        pl_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
                for i in range(len(pl_data["playlist_information"])):
                        pl_list.append(pl_data["playlist_information"][i])
        df1=st.dataframe(pl_list)

        return df1


def show_videos_table():
        vi_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for vi_data in coll1.find({},{"_id":0,"video_information":1}):
                for i in range(len(vi_data["video_information"])):
                        vi_list.append(vi_data["video_information"][i])
        df2=st.dataframe(vi_list)

        return df2

def show_comment_tables():
        com_list=[]
        db=client["Nitish_YouTube_data"]
        coll1=db["channel_details"]
        for com_data in coll1.find({},{"_id":0,"comment_information":1}):
                for i in range(len(com_data["comment_information"])):
                        com_list.append(com_data["comment_information"][i])
        df3=st.dataframe(com_list)

        return df3

#streamlit coding

with st.sidebar:
    st.title(":red[YOUTUBE],:black[DATA HARVERSTING AND WAREHOUSING]")
    st.header("Skill Take Away")
    st.caption("Python Scripting")
    st.caption("Data Collection")
    st.caption("Api Intergration")
    st.caption("MongoDB & SQL")


channel_id=st.text_input("Enter the Channel ID!")

if st.button("collect and store Data"):
    ch_ids=[]
    db=client["Nitish_YouTube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"]["Channel_Id"])


    if channel_id in ch_ids:
        st.success("Channel details is already exists")
    else:
        insert=channel_details(channel_id)
        st.success(insert)

if st.button("Migrate to sql"):
    Table=tables()
    st.success(Table)


show_table=st.radio("Select the table for view",("CHANNELS","PLAYLISTS","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()


elif show_table=="PLAYLISTS":
    show_playlists_table()


elif show_table=="VIDEOS":
    show_videos_table()


elif show_table=="COMMENTS":
    show_comment_tables()

#SQL Connection

mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="nitish",
                        database="Nitish_YouTube_data",
                        port="5432")
cursor=mydb.cursor()

Question=st.selectbox("Select your Question",("1.What are the names of all the videos and their corresponding channels",
                                              "2.Which channels have the most number of videos, and how many videos do they have",
                                              "3.What are the top 10 most viewed videos and their respective channels",
                                              "4.	How many comments were made on each video, and what are their corresponding video names",
                                              "5.	Which videos have the highest number of likes, and what are their corresponding channel names",
                                              "6.	What is the total number of likes and dislikes for each video, and what are their corresponding video names",
                                              "7.	What is the total number of views for each channel, and what are their corresponding channel names",
                                              "8.	What are the names of all the channels that have published videos in the year 2022",
                                              "9.	What is the average duration of all videos in each channel, and what are their corresponding channel names",
                                              "10.	Which videos have the highest number of comments, and what are their corresponding channel names"))


if Question == "1. What are the names of all the videos and their corresponding channels?":

    Q1 = '''select title as videos,channel_name as channelname from videos'''
    cursor.execute(Q1)
    mydb.commit()
    t1 = cursor.fetchall()
    df = pd.DataFrame(t1,columns=['videoTitle','channelName'])
    st.write(df)

elif Question == "2. Which channels have the most number of videos, and how many videos do they have?":

    Q2 = '''select channel_name as channelname, total_videos as no_videos from channels
            order by total_videos desc'''
    cursor.execute(Q2)
    mydb.commit()
    t2 = cursor.fetchall()
    df2 = pd.DataFrame(t2,columns=['channel name','no of videos'])
    st.write(df2)

elif Question == "3. What are the top 10 most viewed videos and their respective channels?":

    Q3 = '''select views as views, title as videotitle, channel_name as channelname from videos
            where views is not null order by views desc limit 10'''
    cursor.execute(Q3)
    mydb.commit()
    t3 = cursor.fetchall()
    df3 = pd.DataFrame(t3,columns=['views','videoTitle','channelName'])
    st.write(df3)

elif Question == "4. How many comments were made on each video, and what are their corresponding video names?":

    Q4 = '''select comments as no_comments, title as videotitle from videos where comments is not null'''
    cursor.execute(Q4)
    mydb.commit()
    t4 = cursor.fetchall()
    df4 = pd.DataFrame(t4,columns=['noOfComments','videoTitle'])
    st.write(df4)

elif Question == "5. Which videos have the highest number of likes, and what are their corresponding channel names?":

    Q5 = '''select title as videotitle, channel_name as channelname, likes as likecount from videos
            where likes is not null order by likes desc'''
    cursor.execute(Q5)
    mydb.commit()
    t5 = cursor.fetchall()
    df5 = pd.DataFrame(t5,columns=['videoTitle','channelName', 'likeCount'])
    st.write(df5)

elif Question == "6. What is the total number of likes for each video, and what are their corresponding video names?":

    Q6 = '''select likes as likecount, title as videotitle from videos'''
    cursor.execute(Q6)
    mydb.commit()
    t6 = cursor.fetchall()
    df6 = pd.DataFrame(t6,columns=['likeCount','videoTitle'])
    st.write(df6)

elif Question == "7. What is the total number of views for each channel, and what are their corresponding channel names?":

    Q7 = '''select channel_name as channelname, views as totalviews from channels'''
    cursor.execute(Q7)
    mydb.commit()
    t7 = cursor.fetchall()
    df7 = pd.DataFrame(t7,columns=['channelName','totalViews'])
    st.write(df7)

elif Question == "8. What are the names of all the channels that have published videos in the year 2022?":

    Q8 = '''select title as videotitle, published_date as videorelease, channel_name as channelname from videos
            where extract(year from published_date)=2022'''
    cursor.execute(Q8)
    mydb.commit()
    t8 = cursor.fetchall()
    df8 = pd.DataFrame(t8,columns=['videoTitle','publisedDate','channelName'])
    st.write(df8)

elif Question == "9. What is the average duration of all videos in each channel, and what are their corresponding channel names?":

    Q9 = '''select channel_name as channelname, avg(duration) as avgduration from videos group by channel_name'''
    cursor.execute(Q9)
    mydb.commit()
    t9 = cursor.fetchall()
    df9 = pd.DataFrame(t9,columns=['channelName','avgDuration'])

    t9 = []
    for index,row in df9.iterrows():
        channel_title = row['channelName']
        avgduration = row['avgDuration']
        avgduration_str = str(avgduration)
        t9.append(dict(channeltitle = channel_title, avgduration = avgduration_str))
    df9_1 = pd.DataFrame(t9)
    st.write(df9_1)

elif Question == "10. Which videos have the highest number of comments, and what are their corresponding channel names?":

    Q10 = '''select title as videotitle, channel_name as channelname, comments as comments from videos where comments is not null order by comments desc'''
    cursor.execute(Q10)
    mydb.commit()
    t10 = cursor.fetchall()
    df10 = pd.DataFrame(t10,columns=['videoTitle','channelName','comments'])
    st.write(df10)