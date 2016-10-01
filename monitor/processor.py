import logging
logger = logging.getLogger(__name__)
logger.debug("processor.py loaded")

import gviz_api
import json
from datetime import datetime, timedelta
from time import mktime

from smartthings import SmartThings

def update_range(old, new):
    if "max" in new:
        if old["max"] is None:
            old["max"] = new["max"]
        else:
            if new["max"] > old["max"]:
                old["max"] = new["max"]
    if "min" in new:
        if old["min"] is None:
            old["min"] = new["min"]
        else:
            if new["min"] < old["min"]:
                old["min"] = new["min"]

def things(st):
    return 1



def results(token):

    logger.debug("results(%s)" % token)
    st = SmartThings(token)

    dates = {
        "bound": {
            "min": None,
            "max": None,
        },
        "default": {
            "min": datetime(2016, 4, 20),
            "max": datetime(2016, 4, 25),
        },
    }

    description = { "Date": "datetime" }
    data = []
    columns_order=["Date"]
    things = st.things("temperature")
    for thing in things[:9]:
        description[thing["label"]] = "number"
        columns_order.append(thing["label"])
        source_data = st.states(
            thing_id=thing["id"],
            state="temperature",
            since=dates["default"]["min"],
            until=dates["default"]["max"],
        )
        update_range(
            dates["bound"],
            st.states_range(
                thing_id=thing["id"],
                state="temperature",
            ),
        )
        logger.debug(
            "range is {0} to {1}"
            .format(dates["bound"]["min"], dates["bound"]["max"])
        )
        #logger.debug("Processing thing: {0}".format(thing))
        logger.debug("Found rows: {0}".format(source_data.count()))
        for row in source_data[:]:
            #logger.debug("Processing row: {0}".format(row))
            if row["date"] is not None and row["value"] is not None:
                value = int(float(row["value"]))
                if value < 150:
                    data.append({
                        "Date": row["date"],
                        thing["label"]: value,
                    })
    # logger.debug("Data: {0}".format(data))
    # Load it into gviz_api.DataTable
    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)
    # Create JavaScript code string
    jscode = data_table.ToJSCode(
        "jscode_data",
        columns_order=columns_order,
        order_by=columns_order[0],
    )

    jsdates = {
        "bound": {
            "min": int(mktime(dates["bound"]["min"].timetuple())) * 1000,
            "max": int(mktime(dates["bound"]["max"].timetuple())) * 1000,
        },
        "default": {
            "min": int(mktime(dates["default"]["min"].timetuple())) * 1000,
            "max": int(mktime(dates["default"]["max"].timetuple())) * 1000,
        },
    }



    return {"jscode": jscode, "dates": jsdates}
