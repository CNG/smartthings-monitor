import logging
logging.basicConfig( filename='app.log', level=logging.DEBUG )
logger = logging.getLogger(__name__)
logger.debug("processor.py loaded")
from pymongo import MongoClient
db = MongoClient().monitor
from smartthings import SmartThings, ACCOUNTS, THINGS, STATES, CALLS

token = "6a2eb151-8247-4ff3-adda-342a9c0f2b20"
st = SmartThings( token )

#db.things.delete_many({})
print "Things collection has {0} documents.".format(db.things.count())
#db.states.delete_many({})
print "States collection has {0} documents.".format(db.states.count())

#things = st.things("thermostat")
#things = st.things("humidity")
things = st.things("temperature")
#things = st.things("all")

#print things.count()

for thing in things[:]:
    states = st.states(thing["id"], "temperature")
    #if states:
        #for state in states:
            #print state

print "Things collection has {0} documents.".format(db.things.count())
print "States collection has {0} documents.".format(db.states.count())
