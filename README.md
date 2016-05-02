## SmartThings Monitor ##

Graph data gathered from [SmartThings][st] devices!

This project is an experiment learning to interact with [SmartThings][st]. I didn't have a specific goal at the outset other than to see what data the service offers and to make some graphs. I expanded the scope as I developed before I even got to any graphing in hopes this could be made useful for others, and to get some experience with a few more technologies.

### How to use

SmartThings Monitor has two main parts:

1. [Web Services SmartApp][wssa] that must be installed to a SmartThings location
2. External application (powered by the code in this repository) to query the API provided by the SmartApp and generate charts, etc.

SmartThings [requires approval](http://docs.smartthings.com/en/latest/smartapp-web-services-developers-guide/authorization.html) before SmartApps can be published by SmartThings and installed automatically. I have not sought such approval, so for now, if anyone else wants to use this app, they must install the code themselves as a custom SmartApp in their own account. That SmartApp code will be published separately and linked from here when I get a chance. 

While the external application code is available in this repository, end users don't need to install anything from here, as it's already running at [https://votecharlie.com/projects/monitor][home]. Anyone can sign up for an account there and use the service provided they have installed the requisite SmartApp.

### How it works

As mentioned above, the SmartThings side API is provided by a [Web Services SmartApp][wssa] users can install to their SmartThings locations and configure with specific permissions for devices. That app is written in [Groovy](http://groovy-lang.org/documentation.html#gettingstarted).

The application code in this repository is based on the [Python](http://python.org/) web framework [web.py](http://webpy.org/). User registration and login is provided by a [modified version](https://github.com/CNG/webpy-mongodb-sessions) of [webpy-mongodb-sessions](https://github.com/jrenaut/webpy-mongodb-sessions), which relies on [MongoDB](https://www.mongodb.org/) and its provided [PyMongo](https://api.mongodb.org/python/current/) module.

Application files in [`monitor`](monitor):

* [`index.py`](monitor/index.py): Main controller for web.py app that allows users to register and connect to an external API to retrieve data for graphing and other uses.
* [`processor.py`](monitor/processor.py): Used by the user results page for graph generation and data handling for display.
* [`smartthings.example.json`](monitor/smartthings.example.json): This file should be copied to `smartthings.json` (removing the `.example` from the filename) and modified to contain the client ID and client secret corresponding to your own installed copy of the Web Services SmartApp. This will not be necessary if I get my own copy approved and published by SmartThings, but for now you'll have to install your own copy of the app from code and get your own ID and secret.
* [`smartthings.py`](monitor/smartthings.py): Main code for interacting with SmartThings and caching the data in a local database.
* [`tasks.py`](monitor/tasks.py): Script designed for scheduled execution to keep data up to date for all users of the app, even when they don't visit the web page and request data for an extended period.
* [`test.py`](monitor/test.py): Not needed for app; just used for development and testing.

The files in [`monitor/templates`](monitor/templates) are processed by web.py to serve front end pages according to the rules defined in `routes` in [`index.py`](monitor/index.py).

[st]: https://www.smartthings.com/
[docs]: http://docs.smartthings.com/en/latest/index.html
[wssa]: http://docs.smartthings.com/en/latest/smartapp-web-services-developers-guide/index.html
[home]: https://votecharlie.com/projects/monitor
