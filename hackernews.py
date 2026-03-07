
import csv

import httpx
import asyncio 



from apscheduler.schedulers.asyncio import AsyncIOScheduler


def save_to_csv (stories):
    
    with open('hackernews_stories.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'URL', 'Score', 'By'])
        for story in stories:
            if story is None : 
                continue
            writer.writerow([story.get('title'), story.get('url'), story.get('score'), story.get('by')])

async def fetch_item(client, id):
    try:
        
        response = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{id}.json')
        return response.json()
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []

async def get_stories():
    try : 
        async with httpx.AsyncClient() as client:
            response = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = response.json()[:20]
            stories = await asyncio.gather(*[fetch_item(client, id) for id in story_ids])
            return stories
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []
    
from dotenv import load_dotenv
import os
import motor.motor_asyncio
load_dotenv()


async def save_to_mongodb(stories):

    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        db = client['hackernews']
        collection = db['stories']
        for story in stories:
            if story is None : 
                continue
            await collection.update_one({'id': story.get('id')}, {'$set': story}, upsert=True)
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")



async def crawl():
    start = time.time()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.run(get_stories()), 'interval', minutes=5)
    scheduler.start()
    stories = asyncio.run(get_stories())
    asyncio.run(save_to_mongodb(stories))
    print(f"Took {time.time() - start:.2f} seconds")

import time

start = time.time()
stories = asyncio.run(get_stories())
asyncio.run(save_to_mongodb(stories))
print(f"Took {time.time() - start:.2f} seconds")
#print(os.getenv("MONGODB_URL"))
#import os
#print(os.getcwd())

