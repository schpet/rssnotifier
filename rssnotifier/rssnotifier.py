import os
import logging
import re
import feedparser

from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import xmpp

class Post(db.Model):
    url = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    description = db.StringProperty()
    shithole = db.BooleanProperty()
    datetime = db.DateTimeProperty()

class MainPage(webapp.RequestHandler):

    def get(self):
        logging.warning("hi")
        illegal_words = [
                "killarney",
                "kits",
                "south vancouver",
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
                "oakridge",
                "squamish",
                "nanaimo",
                "604-805-7278",
                "yaletown",
                "granville",
                "dunbar",
                ]

        posts = []

        im = ""
        feed_url = "http://vancouver.en.craigslist.ca/search/apa/van?query=&srchType=A&minAsk=800&maxAsk=1500&bedrooms=2&format=rss" 
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            post = Post(url = entry.link, title = entry.title, shithole = False)
            description = entry.description.lower()
            
            street = re.search(r"(\d+)(?:st|nd|rd|th)", description)

            if street :
                street_num = int(street.group(1))
                if street_num > 32 :
                    post.shithole = True

            for baddy in illegal_words:

                shithole = post.title.find(baddy)
                if (shithole != -1):
                    post.shithole = True
                    break


                shithole = description.find(baddy)
                if (shithole != -1):
                    post.shithole = True


            posts.append(post)
            if not post.shithole:
                im = im + post.title + '\n' + post.url + '\n\n'
                
        logging.error('mk')
        if self.request.get('im') == 'true':
            logging.error('oh goody')
            user_address = 'schpet@gmail.com'
            chat_message_sent = False

            if xmpp.get_presence(user_address):
                status_code = xmpp.send_message(user_address, im)
                chat_message_sent = (status_code == xmpp.NO_ERROR)
                logging.error(`chat_message_sent` + ' ? ' + im)
            else:
                
                xmpp.send_invite(user_address)
                logging.error('no instant message for you')

        template_values = {
                "posts": posts,
                "feed": feed_url,
                }

        path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
        self.response.out.write(template.render(path, template_values))


""" TODO handle spaces in queries """
application = webapp.WSGIApplication(
        [
            ('/', MainPage),
        ],
        debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
