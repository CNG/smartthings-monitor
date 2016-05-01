import logging
logger = logging.getLogger(__name__)
logger.debug("processor.py loaded")

import gviz_api
import json
from datetime import datetime, timedelta

from smartthings import SmartThings

def results(token):

    logger.debug("results(%s)" % token)
    st = SmartThings(token)
    description = { "Date": "datetime" }
    data = []
    columns_order=["Date"]
    things = st.things("temperature")
    for thing in things[:5]:
        description[thing["label"]] = "number"
        columns_order.append(thing["label"])
        source_data = st.states(
            thing_id=thing["id"],
            state="temperature",
            since=datetime(2016, 4, 20),
            until=datetime(2016, 4, 25),
        )
        logger.debug("Processing thing: {0}".format(thing))
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









    return jscode
