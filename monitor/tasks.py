"""Background tasks for app that allows users to register and connect to an
external API to retrieve data for graphing and other uses. This is intended
to be executed via crontab using a command like the following:

    0 */12 * * * cd /var/www/votecharlie.com/www/projects/monitor/monitor && ../bin/python -u tasks.py >> cron.log 2>&1

TODO:
    Decide whether to use `logging` instead of printing to stdout and consolidate
      `cron.log` that collects the printed statements and `app.log` that collects
      the Logger output.

Author: Charlie Gorichanaz <charlie@gorichanaz.com>

"""
import logging
import smartthings


logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
)
log = logging.getLogger(__name__)

log.debug("tasks.py loaded")


def update_states(account_token, state="all"):
    """Update database with most recent state information.

    Arguments:
        account_token (str): The access token for a particular account's connection
            to the API. This is used to instantiate the API class and make API calls.
        state (Optional[str]): The state type to update. Defaults to "all", which
            retrieves all possible states for all devices to which the user provided
            access. Otherwise if something specific like "temperature" is given,
            selects all devices under that category to which the user provided access,
            and then only retrieves the "temperature" state for those devices.
    """
    st = smartthings.SmartThings(account_token)
    things = st.things(state)
    for thing in things:
        if state is "all":
            for attribute in smartthings.attributes(thing):
                states = st.states(thing["id"], attribute)
        else:
            states = st.states(thing["id"], state)


def print_doc_counts():
    """Print line with count of documents in main collections."""
    for name in smartthings.db.collection_names():
        print "Collection {0} has {1} documents.".format(name, smartthings.db[name].count())


if __name__ == "__main__":
    print_doc_counts()
    for account in smartthings.accounts():
        update_states(account["token"])
        update_states(account["token"], "temperature")
    print_doc_counts()
