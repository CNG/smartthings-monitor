# -*- coding: utf-8 -*-
"""Main controller for app that allows users to register and connect to an
external API to retrieve data for graphing and other uses.

Author: Charlie Gorichanaz <charlie@gorichanaz.com>

"""

# Logging
import logging
logging.basicConfig( filename='app.log', level=logging.DEBUG )
log = logging.getLogger(__name__)
log.debug("index.py loaded")
# Web.py and sessions
import web
from webpy_mongodb_sessions.session import MongoStore
import webpy_mongodb_sessions.users as users
# API interaction, database and data handling
import smartthings, processor
from smartthings import db, SmartThings


"""

SET UP DB AND WEBPY WITH USER LOGIN AND SESSIONS

"""

template_globals = {
    'app_path': lambda p: 'https://votecharlie.com' + web.ctx.homepath + p,
}
render = web.template.render('templates/', globals=template_globals)
routes = (
    '/',          'index',
    '/error',     'error',
    '/connect',   'connect',
    '/login',     'login',
    '/logout',    'logout',
    '/register',  'register',
    '/data/(.+)', 'data',
)
app     = web.application( routes, globals() )
session = web.session.Session(app, MongoStore(db, 'sessions'))
users.session = session
users.collection = db.users


"""

HELPER FUNCTIONS

"""


SHORT_KEY = 'shortcode' # db key to store shortcode


def current_user():
    """Return logged in user"""
    user = users.get_user()
    if user:
        log.debug('user is {0}'.format(user))
        return user
    else:
        log.debug('no user session')
        return None


def new_shortcode(collection, keyname='shortcode', length=5):
    """Generate alphanumeric case sensitive codes until one is found that is not
    already associated with a document in a collection.

    TODO:
        * If 20 attempts fail, currently returns an already used code. Should
            implement a tradeoff where random attempts are made to a point, then
            sort and choose next available code.

    Args:
        collection (pymongo.collection.Collection): Collection to check for
            existing codes.
        keyname (Optional[str]): Name of top level key where in use codes are
            stored in each document.
        length (Optional[int]): Length of each code. Since codes are ASCII
            letters and numbers of any case, total combinations are 62^length.

    Returns:
        str: unused code

    """
    log.debug('generate_shortcode(): starting')
    import random, string
    choices = string.ascii_letters + string.digits
    attempts = 0
    while True:
        shortcode = ''.join(random.choice(choices) for i in range(length))
        attempts += 1
        log.debug(
            'generate_shortcode: attempt {0}: {1}'
            .format(attempts, shortcode)
        )
        if collection.find({keyname: shortcode}).count() == 0 or attempts > 20:
            break
    return shortcode


"""

WEBPY URL HANDLERS

"""


def notfound():
    """Handle 404 not found errors.

    Requires `app.notfound = notfound` following definition.
    """

    return web.notfound(render.error(404))


def internalerror():
    """Handle internal errors.

    Requires `app.internalerror = internalerror` following definition.
    """

    return web.internalerror(render.error(500))


app.notfound      = notfound
app.internalerror = internalerror


class register:
    """Handle user registration."""

    def GET(self):
        log.debug('register.GET')
        return render.register()

    def POST(self):
        log.debug('register.POST')
        params   = web.input()
        username = params["username"]
        password = params["password"]
        user     = users.register(
            username=username,
            password=users.pswd(password, username),
            )
        users.login(user)
        log.debug('register.POST: user is {0}'.format(user))
        raise web.seeother('/')


class profile:
    """Handle user profile viewing and editing."""

    log.debug('profile.GET')
    @users.login_required

    def GET(self):
        return render.profile()


class login:
    """Handle user log in.

    TODO:
        * Information on log in failure.
    """

    def GET(self):
        log.debug('login.GET')
        return render.login()

    def POST(self):
        log.debug('login.POST')
        params = web.input()
        user   = users.authenticate(
            params["username"],
            params["password"],
            )
        if user:
            log.debug('login.POST: user is {0}'.format(user))
            users.login(user)
            raise web.seeother('/')
        else:
            log.error('login.POST: login failed, so user not set')
            raise web.seeother('/error')


class logout:
    """Handle user log out."""

    def GET(self):
        log.debug('logout.GET')
        users.logout() # runs session.kill()
        raise web.seeother('/')


class error:
    """Handle error page."""

    def GET(self):
        log.debug('error.GET')
        return render.error()


class connect:
    """Handle allowing a logged in user to connect to the external API and
    receive an access token, which is stored in the user's account on the local
    database.
    """

    def GET(self):
        log.debug('connect.GET')
        user = current_user()
        if user:
            log.debug('connect.GET: user is {0}'.format(user))
            st = SmartThings()
            params = web.input()
            log.debug('connect.GET: params is {0}'.format(params))
            if 'code' in params:
                # we just logged into SmartThings and got an oauth code
                user['token'] = st.token(params)
                user[SHORT_KEY] = new_shortcode(
                    collection=users.collection,
                    keyname=SHORT_KEY,
                    )
                users.register(**user) # not totally sure why the ** is needed
                result_url = '/data/{0}'.format(user[SHORT_KEY])
                raise web.seeother(result_url)
            else:
                # we are about to redirect to SmartThings to authorize
                raise web.seeother(st.auth_url())
        else:
            log.error('oauth.GET: /connect was accessed without a user session.')
            raise web.seeother('/error')


class index:
    """Handle home page."""

    def GET(self):
        log.debug('index.GET')
        user = current_user()
        if user:
            log.debug('user is {0}'.format(user))
        else:
            log.debug('no user session')
        return render.index(user)


class data:
    """Handle displaying a user's data page."""

    def GET(self, shortcode):
        log.debug('data.GET')
        user = users.collection.find_one({SHORT_KEY: shortcode})
        if user:
            log.debug('data.GET: shortcode {0} matches user {1}'.format(
                shortcode, user))
        else:
            log.debug('data.GET: no user found matching shortcode')
            raise web.seeother('/error')
        return render.data(processor.results(user["token"]))


if __name__ == "__main__":
    app.run()

application = app.wsgifunc()
