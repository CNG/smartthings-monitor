import logging
log = logging.getLogger(__name__)
log.debug("smartthings.py loaded")

import json
from requests_oauthlib import OAuth2Session
import pymongo
from datetime import datetime, timedelta


db = pymongo.MongoClient().monitor


def accounts():
    """Return all accounts with token, meaning they have been connected to API."""
    return [x for x in db.accounts.find() if x["token"] is not None]


def delete_docs(collection=None):
    """TODO DOCS Delete all documents, clearing history and accounts."""
    if collection is None or collection is "accounts":
        db.accounts.delete_many({})
    if collection is None or collection is "things":
        db.things.delete_many({})
    if collection is None or collection is "states":
        db.states.delete_many({})
    if collection is None or collection is "calls":
        db.calls.delete_many({})
    if collection is "users":
        db.users.delete_many({})
    if collection is "sessions":
        db.sessions.delete_many({})


class SmartThings(object):
    """Handle basic API access as well as caching results for data types
    such as states.
    """

    def __init__(self, token=None):
        """Set up instance and prepare to make API requests if token given."""
        log.debug("SmartThings initialized using token {0}".format(token))
        api_base = "https://graph.api.smartthings.com/"
        self._options = {
            "scope":         ["app"],
            "authorize_url": api_base + "oauth/authorize",
            "token_url":     api_base + "oauth/token",
            "endpoints_url": api_base + "api/smartapps/endpoints",
            "client_file":   "smartthings.json",
        }
        self._credentials = {}
        self._token = token
        self._token_dict = None
        self._oauth = {}
        self._endpoint = []
        if self._token: self._load(self._token)
        self._load_credentials()
        self._start_session()

    def _load_credentials(self):
        """Load client ID, client secret and redirect URI from file."""
        filename = self._options["client_file"]
        with open(filename) as data:
            self._credentials = json.load(data)

    def _start_session(self):
        """Start OAuth2 session using stored credentials and token."""
        log.debug("_start_session: using token {0}".format(self.token))
        self._oauth = OAuth2Session(
            self._credentials["client_id"],
            redirect_uri=self._credentials["redirect_uri"],
            scope=self._options["scope"],
            token=self._token_dict,
        )

    def auth_url(self):
        """Get URL for obtaining OAuth2 token."""
        authorization_url, state = self.oauth.authorization_url(
            self._options["authorize_url"],
        )
        return authorization_url

    def token(self, data=None):
        """Get saved token if we already have endpoint saved, otherwise obtain
        token from API using OAuth2 code from given data.

        Todo:
            This function accidentally got used for both callback handling
            and simple getting. Evaluate whether this is sensible.

        Args:
            data (Optional[dict]): HTTP request parameters from API.

        Returns:
            Token from logged in account.

        """
        if not self._token:
            token = self._oauth.fetch_token(
                self._options["token_url"],
                code=data.code,
                client_secret=self._credentials["client_secret"],
            )
            self._token = token["access_token"]
            self._token_dict = token
            self.endpoint() # might as well get endpoints right away
        return self._token

    def endpoint(self):
        """Get endpoint for API calls from self if stored or API otherwise."""
        if not self._endpoint:
            api_endpoint   = self._oauth.get(self._options["endpoints_url"]).json()[0]["uri"]
            app_endpoint   = "{0}/endpoint".format(api_endpoint)
            self._endpoint = app_endpoint
            self._save()   # save endpoints to db with token
        return self._endpoint

    def _save(self):
        """Store token data and endpoint in accounts if we have a token."""
        if self._token:
            db.accounts.update_one(
                {"token": self._token},
                {"$set": {
                        "token_dict": self._token_dict,
                        "endpoint":   self._endpoint,
                    }
                },
                upsert=True,
            )

    def _load(self, token):
        """Get token data and endpoint from database for given token.

        Args:
            token (str): Token from account we want to retrieve full data.
        """
        account = db.accounts.find_one(
            {"token": token},
        )
        self._token_dict = account['token_dict']
        self._endpoint   = account['endpoint']

    def _get_query_time(self, params):
        """Get time of last query with given params.

        Args:
            params (dict): Data characterizing a query.

        Returns:
            datetime.datetime matching last query or Jan. 1, 1900, if no cache.

        """
        # add instance info to dict
        params = dict(
            params,
            token=self.token(),
        )
        # get existing query record
        document = db.calls.find_one(params)
        if document and "date" in document:
            # return date of original record
            return document["date"]
        # arbitrary old date since no record exists
        return datetime(1900, 1, 1)

    def _set_query_time(self, params):
        """Set to now time of last query with given params, ignoring "since".

        Args:
            params (dict): Data characterizing a query. "since" is ignored.

        """
        # "since" is not set when query date retrieved, so ignore.
        params.pop("since", None)
        # Add instance info to dict.
        params = dict(
            params,
            token=self.token(),
        )
        # Update or insert query record with now().
        db.calls.update_one(
            params,
            {"$set": {"date": datetime.now()}},
            upsert=True,
        )

    def _get(self, params, freshness=120):
        """Get data from API if cache for given params is stale. Uses
        _get_query_time() and _set_query_time() to determine staleness.

        Args:
            params (dict): Parameters for the API request. Key `function` is the
                type of data desired, such as `things` or `states`.
            freshness (Optional[int]): Number of minutes after which a new API
                call will be made.

        Returns:
            Response if new API call was made or None if cache is fresh.

        """
        last_datetime = self._get_query_time(params)
        # Add "since" to params unless we're just getting thing list.
        if "function" in params and params["function"] is not "things":
            last_delta = last_datetime - datetime(1970, 1, 1)
            params["since"] = last_delta.total_seconds()
            #params["since"] = 0 # TODO REMOVE THIS LINE AFTER DATA REGATHERED
        # Check if cache is fresh enough to skip API.
        cutoff = datetime.now() - timedelta(minutes = freshness)
        if last_datetime and last_datetime > cutoff:
            log.debug(
                "_get: Skipping; got {0} within {1} minutes."
                .format(params["function"].encode("utf-8"), freshness)
            )
            return None # TODO UNCOMMENT THIS LINE AFTER DATA REGATHERED
        # Check for rate limiting.
        while True:
            response = self._oauth.request(
                "get",
                self.endpoint(),
                params=params
            )
            # Extract needed HTTP headers to variables.
            limit, current, ttl = [
                response.headers.get("x-ratelimit-{0}".format(k))
                for k in ['limit', 'current', 'ttl']
            ]
            log.debug(
                "_get: Limit {0}, Current {1}, TTL {2}"
                .format(limit, current, ttl)
            )
            if(response.status_code == 429):
                log.debug("_get: RATE LIMITED, waiting...")
                import time
                if ttl:
                    time.sleep(ttl)
                else:
                    time.sleep(1)
            else:
                self._set_query_time(params)
                break
        return response

    def things(self, kind="all", refresh=False):
        """Get things, optionally of only a certain type. API is queried
        for thing data only if any cached data is more than 10 minutes old.

        Args:
            kind (Optional[str]): Limit to things of this kind. Default: `all`.
            refresh (Optional[bool]): Force refreshing things from API.
        Returns:
            Collection of things.

        """
        freshness = 0 if refresh else 10 #  minutes
        params = {
            "function": "things",
            "kind": kind,
        }
        response = self._get(params, freshness)
        if response is not None:
            data = [x for x in response.json() if x is not None]
            # instead of figuring out which things no longer get returned,
            # set all "active" fields to false first and add with true
            db.things.update_many(
                { "token": self.token() },
                { "$set": {
                        "active": False,
                    }
                },
            )
            # insert retrieved things into database
            inserted_count = 0
            for item in data:
                item["token"]  = self.token()
                item["active"] = True
                result = db.things.replace_one(
                    {
                        "token": self.token(),
                        "id":    item["id"],
                    },
                    item,
                    upsert=True,
                )
                if result.upserted_id:
                    inserted_count += 1
            log.debug(
                "things: Saved {0} things: {1} new, {2} replaced."
                .format(len(data), inserted_count, len(data) - inserted_count)
            )
        # Get final data from database
        return db.things.find({
            "active": True,
            "token":  self.token(),
        })

    def thing(self, thing_id):
        """Get thing with a given ID.

        Args:
            thing_id (str): Limit to the thing with this ID.
        Returns:
            Thing.

        """
        return db.things.find_one({
            "token": self.token(),
            "id":    thing_id,
        })

    def states_range(self, thing_id, state=None):
        """Get date range of stored states for the thing with a given ID.

        Args:
            thing_id (str): Limit to the thing with this ID.
            state (Optional[str]): Limit to this type of state.
        Returns:
            Dictionary with `min` and `max` keys corresponding to dates of
            the extreme data points for specified state.

        """
        # First update local database from API.
        self.states(thing_id, state)
        # Query local database for all states sorted by date.
        params = {
            "thing_id": thing_id,
        }
        if state is not None:
            params["state"] = state
        cursor = db.states.find(params).sort([
            ("date", pymongo.ASCENDING),
        ])
        # Return dates of first and last items.
        return {
            "min": cursor[0]["date"],
            "max": cursor[cursor.count()-1]["date"],
        }

    def states(self, thing_id, state=None, since=None, until=None):
        """Get states for the thing with a given ID. First call self._get() to
        retrieve from the API the maximum numbers of states possible since last
        retrieval. Add the new states to the local database. Then return from
        the local database states matching given criteria.

        Args:
            thing_id (str): Limit to the thing with this ID.
            state (Optional[str]): Limit to this type of state.
            since (Optional[datetime]): Limit to results on or after this time.
            until (Optional[datetime]): Limit to results before this time.
        Returns:
            Collection of states.

        """

        def _params(kind):
            """Build appropriate params. `kind` can be `api` or `db`."""
            params = {
                "thing_id": thing_id,
            }
            if state is not None:
                params["state"] = state
            if kind is "api":
                params["function"] = "states"
            if kind is "db":
                if since is not None:
                    if until is not None:
                        params["date"] = { "$gte": since, "$lt": until }
                    else:
                        params["date"] = { "$gte": since }
                else:
                    if until is not None:
                        params["date"] = { "$lt": until }
            return params

        # Make request and store any returned data.
        response = self._get(_params(kind="api"))
        if response is not None:
            data = [x for x in response.json() if x is not None]
            inserted_count = 0
            for item in data:
                if not isinstance(item, dict):
                    # Sometimes API returns empty items.
                    break
                item["thing_id"]  = thing_id
                # Convert string date to Python date.
                item["date"]      = datetime.strptime(item["date"],'%Y-%m-%dT%H:%M:%SZ')
                # Insert retrieved things into database, overwriting any duplicates.
                result = db.states.replace_one(
                    {
                        "thing_id": thing_id,
                        "state":    state,
                        "date":     item["date"],
                    },
                    item,
                    upsert=True,
                )
                if result.upserted_id:
                    inserted_count += 1
            log.debug(
                "states: Saved {0} states: {1} new, {2} replaced."
                .format(len(data), inserted_count, len(data) - inserted_count)
            )
        # Get final data from database.
        return db.states.find(_params(kind="db"))


def attributes(thing):
    attributes = set()
    for capability in thing["capabilities"]:
        for attribute in capability["attributes"]:
            attributes.add(attribute)
    return attributes
