from bs4 import BeautifulSoup
import requests
import csv

with open('cms_scrape.csv', 'w') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['headline', 'summary', 'video_link'])
    source = requests.get('http://coreyms.com').text
    soup = BeautifulSoup(source, 'lxml')

    threads = []

    for article in soup.find_all('article'):
        headline = article.h2.a.text
        summary = article.find('div', class_='entry-content').p.text

        try:
            yt_link = f'https://youtube.com/watch?v={article.find("iframe", class_="youtube-player")["src"].split("/")[4].split("?")[0]}'
        except Exception as e:
            yt_link = None

        t = threading.Thread(target=csv_writer.writerow, args=([headline, summary, yt_link]))
        threads.append(t)
        t.start()

for thread in threads:
    thread.join()

csv_file.close()
