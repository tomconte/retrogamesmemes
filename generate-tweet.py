import os
import random
import re

import requests
import tweepy
from langchain.chains import LLMChain, SimpleSequentialChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import BaseOutputParser
from dotenv import load_dotenv

# Load environment variables using dotenv
load_dotenv()

class ParagraphOutputParser(BaseOutputParser):
    def parse(self, text: str):
        paragraphs = text.splitlines()
        paragraphs = [p for p in paragraphs if len(p) > 0]
        return paragraphs


# Secrets, etc.

twitter_bearer = os.environ.get("TWITTER_BEARER")
twitter_consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
twitter_consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
twitter_access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
twitter_access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

google_developer_key = os.environ.get("GOOGLE_DEVELOPER_KEY")
google_custom_search_engine_id = os.environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")


def post_twitter_thread(game_title, platform, messages):
    # Remove all hashtags from the messages using regular expressions
    # messages = [re.sub(r"#\w+", "", message) for message in messages]

    # Check that all messages are less than the length limit of a tweet
    for message in messages:
        if len(message) > 280:
            print(len(message), message)
            raise ValueError("A message is too long! Max length is 280 characters.")

    # Get the image url using game_title and platform
    image_url = get_image_url(f"box art {game_title} {platform}")

    # Download the image from the URL
    image_data = requests.get(image_url).content

    # Save the image data to a temporary file
    with open("image.jpg", "wb") as f:
        f.write(image_data)

    # Create API v2 client
    api = tweepy.Client(
        consumer_key=twitter_consumer_key,
        consumer_secret=twitter_consumer_secret,
        access_token=twitter_access_token,
        access_token_secret=twitter_access_token_secret,
    )

    # Create API v1 client
    auth = tweepy.OAuth1UserHandler(
        twitter_consumer_key,
        twitter_consumer_secret,
        twitter_access_token,
        twitter_access_token_secret,
    )

    api_v1 = tweepy.API(auth=auth)

    # Upload the image to Twitter
    media_upload = api_v1.media_upload(
        filename="image.jpg",
    )

    # Post the first message in the thread
    first_tweet = api.create_tweet(
        text=messages[0],
        media_ids=[media_upload.media_id_string],
    )

    # Loop through the remaining messages and reply to the previous tweet
    previous_tweet = first_tweet
    for message in messages[1:]:
        tweet = api.create_tweet(
            text=message,
            in_reply_to_tweet_id=previous_tweet.data["id"],
        )
        previous_tweet = tweet


# Function that will look for an image on Google Images and return the URL of the first image
def get_image_url(keywords):
    # Import the Google Images Search API
    from google_images_search import GoogleImagesSearch

    # Create an instance of the GoogleImagesSearch class
    gis = GoogleImagesSearch(google_developer_key, google_custom_search_engine_id)

    # Define the search parameters
    _search_params = {
        "q": keywords,
        "num": 1,
        "safe": "high",
        "fileType": "jpg",
        "imgType": "photo",
    }

    # Perform the search and get the results
    gis.search(search_params=_search_params)
    results = gis.results()

    # Return the URL of the first image
    return results[0].url


def generate_content(game_title, platform):
    template = """You are a bot that generates engaging content to be posted on social networks.
    You are very knowledgeable about vintage 8-bit computers and old computer games from the eighties.
    I will give you the name of computer game, and you will generate a short 
    text telling an anecdote about the game or describing a particularly
    memorable aspect of the game.
    Your style should be vivid, epic and inspiring but concise with short sentences.
    You can make moderate use of emojis.
    You will split the text into several lines of maximum 250 characters each to be shared as a thread on Twitter."""

    system_message_prompt = SystemMessagePromptTemplate.from_template(template)

    content_prompt_template = 'Game title: "{game_title}" on platform: "{platform}".'
    content_message_prompt = HumanMessagePromptTemplate.from_template(
        content_prompt_template
    )

    content_chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt, content_message_prompt]
    )

    content_chain = LLMChain(
        llm=ChatOpenAI(),
        prompt=content_chat_prompt,
        output_parser=ParagraphOutputParser(),
        verbose=True,
    )

    result = content_chain.run(game_title=game_title, platform=platform)

    return result


def main():
    # Read all the lines from the file best-games-total.txt and put them in a list
    with open("best-games-total.txt", "r") as f:
        lines = f.readlines()
    # Pick a line at random from the list
    line = random.choice(lines).strip()
    # Split the line using comma as a separator into game_title and platform
    game_title, platform = line.split(",")

    result = generate_content(game_title, platform)

    print(result)

    post_twitter_thread(game_title, platform, result)


if __name__ == "__main__":
    main()
