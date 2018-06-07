import web

db = web.database(dbn='sqlite',
        db='AuctionBase' #TODO: add your SQLite database filename
    )

######################BEGIN HELPER METHODS######################

# Enforce foreign key constraints
# WARNING: DO NOT REMOVE THIS!
def enforceForeignKey():
    db.query('PRAGMA foreign_keys = ON')

# initiates a transaction on the database
def transaction():
    return db.transaction()
# Sample usage (in auctionbase.py):
#
# t = sqlitedb.transaction()
# try:
#     sqlitedb.query('[FIRST QUERY STATEMENT]')
#     sqlitedb.query('[SECOND QUERY STATEMENT]')
# except Exception as e:
#     t.rollback()
#     print str(e)
# else:
#     t.commit()
#
# check out http://webpy.org/cookbook/transactions for examples

# returns the current time from your database
def getTime():
    # TODO: update the query string to match
    # the correct column and table name in your database
    query_string = 'SELECT Time FROM CurrentTime'
    results = query(query_string)
    # alternatively: return results[0]['currenttime']
    return results[0].Time # TODO: update this as well to match the
                                  # column name

# returns a single item specified by the Item's ID in the database
# Note: if the `result' list is empty (i.e. there are no items for a
# a given ID), this will throw an Exception!
def getItemById(item_id):
    # TODO: rewrite this method to catch the Exception in case `result' is empty
    query_string = 'SELECT * FROM Items WHERE ItemID = $itemID'
    result = query(query_string, {'itemID': item_id})
    if(result) :
	return result[0]
    else :
	return None

def getUserById(user_id):
    query_string = 'SELECT * FROM Users WHERE UserID = $userID'
    result = query(query_string, { 'userID': user_id })
    if(result) :
        return result[0]
    else :
        return None

def getLatestBidByItemID(item_id):
    query_string = 'SELECT * FROM Bids WHERE ItemID = $itemID ORDER BY Time DESC LIMIT 1'
    result = query(query_string, { 'itemID': item_id })
    if(result) :
        return result[0]
    else :
        return None

def getAllBidsByItemID(itemID) :
    query_string = 'SELECT * FROM Bids WHERE ItemID=$item_id ORDER BY Time'
    results = db.query(query_string, vars = { 'item_id' : itemID })
    return results

def getAllCategoriesByItemID(itemID) :
    query_string = 'SELECT DISTINCT Categories.Category FROM Items INNER JOIN Categories ON (Items.ItemID = Categories.ItemID) WHERE Items.ItemID=$item_id'
    results = db.query(query_string, vars = { 'item_id' : itemID })
    return results

def addNewBidToDatabase(itemID, userID, amount):
    item = getItemById(itemID)
    buyPrice = item['Buy_Price']
    query_string = 'INSERT INTO Bids (ItemID, UserID, Amount, Time) VALUES ($item_id, $user_id, $new_price, $curr_time)'
    if buyPrice and float(amount) >= float(buyPrice) :
        t = transaction()
        try:
            db.query(query_string, vars = { 'item_id' : itemID, 'user_id' : userID, 'new_price' : buyPrice, 'curr_time' : getTime() })
            db.query('UPDATE Items SET Ends=$curr_time WHERE ItemID=$item_id', vars = { 'curr_time' : getTime(), 'item_id' : item['ItemID'] })
        except Exception as e:
            t.rollback()
            print str(e)
        else:
            t.commit()
        return

    else :
        t = transaction()
        try:
            db.query(query_string, vars={ 'item_id' : itemID, 'user_id' : userID, 'new_price' : amount, 'curr_time' : getTime() })
        except Exception as e:
            t.rollback()
            print str(e)
        else:
            t.commit()
        return

# wrapper method around web.py's db.query method
# check out http://webpy.org/cookbook/query for more info
def query(query_string, vars = {}):
    return list(db.query(query_string, vars))

#####################END HELPER METHODS#####################

#TODO: additional methods to interact with your database,
# e.g. to update the current time

def setTime(input):
    currentTime = db.query('SELECT * FROM CurrentTime')
    
    if(input < currentTime[0]['Time']) :
        return False

    t = transaction()
    try:
        db.query('DELETE FROM CurrentTime')
        db.query('INSERT INTO CurrentTime VALUES ($input_string)', vars={ 'input_string' : input })
    except Exception as e:
        t.rollback()
        print str(e)
    else:
        t.commit()

    return True

# Method to create new bids based on the itemID, userID and the value of the new bid
def createNewBid(itemID, price, userID) :
    item = getItemById(itemID)
    user = getUserById(userID)
    if(item and user) :
        if(item.Seller_UserID == user.UserID):
            return False

        latestBid = getLatestBidByItemID(itemID)

        if latestBid :
            if (latestBid['Time'] == getTime()) :
                return False
            if (price <= latestBid['Amount']) :
                return False

        startTime = item['Started']
        endTime = item['Ends']
        currTime = getTime()

        if(currTime < startTime or currTime > endTime) :
            return False

        addNewBidToDatabase(itemID, userID, price)
        return True
    else :
        return False

# Find the results given the search terms entered by the user
def findResults(itemID, category, description, status, minPrice, maxPrice) :
    query_string = 'SELECT DISTINCT * FROM Items'

    if(category) :
        query_string += ' INNER JOIN Categories ON (Items.ItemID = Categories.ItemID)'
    
    conditions = []

    if(itemID) :
        conditions.append("Items.ItemID=%s" %(itemID))

    if(category) :
        conditions.append("Categories.Category='%s'" %(category))

    if(description) :
        conditions.append("DESCRIPTION LIKE '%" + description + "%'")

    if(status) :
        curr_time = getTime()
        if(status=='open') :
            conditions.append("Started<='%s' AND Ends>='%s' AND Currently<Buy_Price" %(curr_time, curr_time))
        elif (status=='close') :
            conditions.append("Ends<='%s' OR Currently=Buy_Price" %(curr_time))
        elif (status=='notStarted') :
            conditions.append("Started>'%s'" %(curr_time))

    if(minPrice) :
        conditions.append("Currently>=%s" %(minPrice))

    if(maxPrice) :
        conditions.append("Currently<=%s" %(maxPrice))

    if(any(conditions)) :
        query_string += ' WHERE '
        while (len(conditions)>0) :
            query_string += '(' + conditions[0] + ')'
            del conditions[0]
            if(len(conditions)>0) :
                query_string += ' AND '

    results = db.query(query_string)
    if results :
        return results
    else :
        return None
