#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
import sqlitedb
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

###########################################################################################
##########################DO NOT CHANGE ANYTHING ABOVE THIS LINE!##########################
###########################################################################################

######################BEGIN HELPER METHODS######################

# helper method to convert times from database (which will return a string)
# into datetime objects. This will allow you to compare times correctly (using
# ==, !=, <, >, etc.) instead of lexicographically as strings.

# Sample use:
# current_time = string_to_time(sqlitedb.getTime())

def string_to_time(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

# helper method to render a template in the templates/ directory
#
# `template_name': name of template file to render
#
# `**context': a dictionary of variable names mapped to values
# that is passed to Jinja2's templating engine
#
# See curr_time's `GET' method for sample usage
#
# WARNING: DO NOT CHANGE THIS METHOD
def render_template(template_name, **context):
    extensions = context.pop('extensions', [])
    globals = context.pop('globals', {})

    jinja_env = Environment(autoescape=True,
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
            extensions=extensions,
            )
    jinja_env.globals.update(globals)

    web.header('Content-Type','text/html; charset=utf-8', unique=True)

    return jinja_env.get_template(template_name).render(context)

#####################END HELPER METHODS#####################

urls = ('/currtime', 'curr_time',
        '/selecttime', 'select_time',
	'/addbid', 'add_bid',
        '/search', 'search',
        '/itemdetail', 'item_detail'
        # TODO: add additional URLs here
        # first parameter => URL, second parameter => class name
        )

class curr_time:
    # A simple GET request, to '/currtime'
    #
    # Notice that we pass in `current_time' to our `render_template' call
    # in order to have its value displayed on the web page
    def GET(self):
        current_time = sqlitedb.getTime()
        return render_template('curr_time.html', time = current_time)

class select_time:
    # Aanother GET request, this time to the URL '/selecttime'
    def GET(self):
        return render_template('select_time.html')

    # A POST request
    #
    # You can fetch the parameters passed to the URL
    # by calling `web.input()' for **both** POST requests
    # and GET requests
    def POST(self):
        post_params = web.input()
        MM = post_params['MM']
        dd = post_params['dd']
        yyyy = post_params['yyyy']
        HH = post_params['HH']
        mm = post_params['mm']
        ss = post_params['ss'];
        enter_name = post_params['entername']


        selected_time = '%s-%s-%s %s:%s:%s' % (yyyy, MM, dd, HH, mm, ss)
        update_message = '(Hello, %s. Previously selected time was: %s.)' % (enter_name, selected_time)
        # TODO: save the selected time as the current time in the database
        result = sqlitedb.setTime(selected_time)

        if result:
            return render_template('select_time.html', message = update_message)

        return render_template('select_time.html', message = 'Enter a Valid Time')
	#TODO xx
	
        # Here, we assign `update_message' to `message', which means
        # we'll refer to it in our template as `message'

class add_bid:
    def GET(self):
        return render_template('add_bid.html')

    def POST(self):
        post_params = web.input()

        itemID = post_params['itemID']
        price = post_params['price']
        userID = post_params['userID']

        if(not itemID or not price or not userID):
            return render_template('add_bid.html', message='Fill Remaining Incomplete Fields', add_result=False)
        else:
            result = sqlitedb.createNewBid(itemID, price, userID)
            return render_template('add_bid.html', add_result=result)

class search :
    def GET(self) :
        return render_template('search.html')

    def POST(self) :
        post_params = web.input()

        itemID = post_params['itemID']
        category = post_params['category']
        description = post_params['description']
        status = post_params['status']
        minPrice = post_params['minPrice']
        maxPrice = post_params['maxPrice']

        results = sqlitedb.findResults(itemID, category, description, status, minPrice, maxPrice)

        if(results) :
            return render_template('search.html', search_result = results)
        else :
            return render_template('search.html')        

class item_detail :
    def GET(self) :
        post_params = web.input()
        itemID = post_params['itemID']
        result = sqlitedb.getItemById(itemID)
        isAuctionClosed = False
        latestBid = None
        if(sqlitedb.getTime() > result['Ends'] or result['Currently']>=result['Buy_Price']) :
            isAuctionClosed = True
            latestBid = sqlitedb.getLatestBidByItemID(itemID)
        bids = sqlitedb.getAllBidsByItemID(post_params['itemID'])
        categories = sqlitedb.getAllCategoriesByItemID(post_params['itemID'])

        return render_template('item_detail.html', item=result, isAuctionClosed=isAuctionClosed,
            latestBid=latestBid, bids=bids, categories=categories)

###########################################################################################
##########################DO NOT CHANGE ANYTHING BELOW THIS LINE!##########################
###########################################################################################

if __name__ == '__main__':
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(sqlitedb.enforceForeignKey))
    app.run()
