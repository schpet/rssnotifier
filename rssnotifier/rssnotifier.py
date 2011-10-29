import os
import logging
import re
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

class Post(db.Model):
    url = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    shithole = db.BooleanProperty()
    datetime = db.DateTimeProperty()

class Scrape(db.Model):
    start = db.DateTimeProperty()
    finish = db.DateTimeProperty()
    feed = db.StringProperty(required=True)

class ScrapeRequest(webapp.RequestHandler):
    def scrape(self):
        feed_url = "http://vancouver.en.craigslist.ca/search/apa/van?query=&srchType=A&minAsk=800&maxAsk=1500&bedrooms=2&format=rss" 
        scrape = Scrape(feed = feed_url, start = datetime.now())

        illegal_words = [
                "killarney",
                "kits",
                "south van",
                "renfrew",
                "kerrisdale",
                "joyce",
                "abbotsford",
                "surrey",
                "comox",
                "marpole",
                "marple",
                "rupert",
                "rentersinvancouver.ca",
                "fraserview",
                "basement",
                "bsmt",
                "oakridge",
                "squamish",
                "nanaimo",
                "604-805-7278",
                "yaletown",
                "granville",
                "dunbar",
                "coquitlam",
                "burnaby",
                ]

        feed = feedparser.parse(feed_url)

        im = ""

        for entry in feed.entries:
            url = entry.link

            existing = Post.get_by_key_name(url)
            
            if not existing:

                date = parse(entry.date)
                post = Post(key_name = url,
                        url = url, 
                        title = entry.title, 
                        shithole = False,
                        datetime = date,
                        )

                description = entry.title.lower() + ' ' + entry.description.lower()
                # bug! only checks the first number found
                # e.g. it's available on the 3rd. 49th and main
                # get rid of anything past 32nd
                street = re.search(r"(\d+)(?:st|nd|rd|th)", description)

                if street:
                    street_num = int(street.group(1))
                    if street_num > 32 :
                        post.shithole = True

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
            message = 'initial complete.'
        
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(message)


class MainPage(webapp.RequestHandler):
    def get(self):
        good_posts = db.GqlQuery("SELECT * "
                                "FROM Post "
                                "WHERE shithole = :1 "
                                "ORDER BY datetime DESC LIMIT 20",
                                False
                                )
        bad_posts = db.GqlQuery("SELECT * "
                                "FROM Post "
                                "WHERE shithole = :1 "
                                "ORDER BY datetime DESC LIMIT 20",
                                True
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
