
from googleapiclient.discovery import build

api_key = '#YOURAPIKEY'

youtube = build('youtube', 'v3', developerKey=api_key)

request = youtube.channels().list(
        part='statistics',
        forUsername='schafer5'
    )

response = request.execute()

print(response)
