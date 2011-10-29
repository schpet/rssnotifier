import os
import logging

import feedparser

from google.appengine.dist import use_library
use_library('django', '1.2')

from dateutil.parser import parse
from datetime import datetime, timedelta

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import xmpp

user_address = '' # put your email here to receive instant messages
branch = 'zack'

feed_urls = { 
        'Vancouver': "http://vancouver.en.craigslist.ca/search/apa/van?query=&srchType=A&minAsk=800&maxAsk=1200&bedrooms=2&format=rss",
        'Burnaby': "http://vancouver.en.craigslist.ca/search/apa/bnc?query=&srchType=A&minAsk=800&maxAsk=1200&bedrooms=2&format=rss",
        'Slurry': "http://vancouver.en.craigslist.ca/search/apa/rds?query=&srchType=A&minAsk=800&maxAsk=1200&bedrooms=2&format=rss",
        }

illegal_words = [
        "killarney",
        "kits",
        "south van",
        "kerrisdale",
        "abbotsford",
        "comox",
        "marpole",
        "marple",
        "rentersinvancouver.ca",
        "basement",
        "bsmt",
        "oakridge",
        "squamish",
        "604-805-7278",
        "yaletown",
        "granville",
        "dunbar",
        ]

class Post(db.Model):
    url = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    shithole = db.BooleanProperty()
    hood = db.StringProperty()
    datetime = db.DateTimeProperty()
    branch = db.StringProperty(default=branch)

class Scrape(db.Model):
    start = db.DateTimeProperty()
    finish = db.DateTimeProperty()
    feed = db.StringProperty(required=True)
    branch = db.StringProperty(default=branch)

class ScrapeRequest(webapp.RequestHandler):
    def scrape(self):
        for hood, feed_url in feed_urls.items():
            scrape = Scrape(feed = feed_url, start = datetime.now())

            feed = feedparser.parse(feed_url)

            im = ""

            for entry in feed.entries:
                url = entry.link + "#!/branch=" + branch

                existing = Post.get_by_key_name(url)
                
                if not existing:

                    date = parse(entry.date)
                    post = Post(key_name = url,
                            url = url, 
                            title = entry.title, 
                            shithole = False,
                            datetime = date,
                            hood = hood,
                            )

                    description = entry.title.lower() + ' ' + entry.description.lower()

                    """
                    I don't think zack is pretentious enough to eliminate
                    streets from his search.

                    # bug! only checks the first number found
                    # e.g. it's available on the 3rd. 49th and main
                    # get rid of anything past 32nd
                    street = re.search(r"(\d+)(?:st|nd|rd|th)", description)

                    if street:
                        street_num = int(street.group(1))
                        if street_num > 32 :
                            post.shithole = True

                    """

                    for bad in illegal_words:
                        shithole = description.find(bad)
                        if (shithole != -1):
                            post.shithole = True

                    if not post.shithole:
                        im = im + post.title + '\n' + post.url + '\n\n'

                    # todo batch put
                    post.put()

            if len(im) > 0 and len(user_address) > 0:
                chat_message_sent = False

                if xmpp.get_presence(user_address):
                    status_code = xmpp.send_message(user_address, im)
                    chat_message_sent = (status_code == xmpp.NO_ERROR)
                    logging.warning(`chat_message_sent` + ' ? ' + im)
                else:
                    xmpp.send_invite(user_address)
                    logging.error('no instant message for you')

            scrape.finish = datetime.now()
            scrape.put()
            

    def get(self):
        scrape_time = None
        message = None
        scrape = Scrape.all().order("-finish").fetch(1)

        if scrape:
            scrape_time = scrape[0].start
            now = datetime.now()
            time_since_scrape = (now - scrape_time)


            if time_since_scrape > timedelta(minutes = 1):
                self.scrape()
                message = 'scrape complete.' 
            else:
                wait_seconds = 60 - time_since_scrape.seconds
                message = 'can\'t scrape for %d seconds.' % wait_seconds
        else:
            self.scrape()
            message = 'initial scrape complete.'
        
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(message)


class MainPage(webapp.RequestHandler):
    def get(self):
        good_posts = db.GqlQuery("SELECT * "
                                "FROM Post "
                                "WHERE shithole = :1 "
                                "AND branch = :2 "
                                "ORDER BY datetime DESC LIMIT 20",
                                False, 
                                branch
                                )
        bad_posts = db.GqlQuery("SELECT * "
                                "FROM Post "
                                "WHERE shithole = :1 "
                                "AND branch = :2 "
                                "ORDER BY datetime DESC LIMIT 20",
                                True,
                                branch
                                )


        scrape = Scrape.all().order("-finish").fetch(1)
        scrape_time = None
        if scrape:
            scrape_time = scrape[0].finish


        template_values = {
                "good_posts": good_posts,
                "bad_posts": bad_posts,
                "scrape_time": scrape_time,
                }

        path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
        self.response.out.write(template.render(path, template_values))


application = webapp.WSGIApplication(
        [
            ('/', MainPage),
            ('/scrape', ScrapeRequest),
        ],
        debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
