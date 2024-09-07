"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to export historical device events from Mist API and save the result 
and a summary in CSV files.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       required for Org reports. Set the org_id    
-q, --q_params=     list of query parameters. Please see the possible filters
                    in https://doc.mist-lab.fr
                    format: -q key1:value1 -q key2:value2 -q ...

-p, --prefix=       define the prefix of the output files. Two files will be genereated:
                    <prefix>_report.csv: list all the events
                    <prefix>_summary.csv: list all the sites (with the dashboad URL)
                    default is "org_events"
-t, --timestamp     append the timestamp at the end of the report and summary files

-l, --log_file=     define the filepath/filename where to write the logs
                    default is {LOG_FILE}
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is {ENV_FILE}

-------
Examples:
python3 ./export_search.py                  
python3 ./export_searchs.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --report=client_sessions_wireless --q_params=duration:1w  
    """

#### IMPORTS ####
import sys
import json
import csv
import os
import logging
import getopt
import datetime

MISTAPI_MIN_VERSION = "0.45.1"

try:
    import mistapi
    from mistapi.__api_response import APIResponse
    from mistapi.__logger import console
except:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)


#### PARAMETERS #####

LOG_FILE = "./script.log"
ENV_FILE = os.path.join(os.path.expanduser("~"), ".mist_env")


#### LOGS ####
logger = logging.getLogger(__name__)
out = sys.stdout


def _query_param_input(query_param_name: str, query_param_type: type) -> any:  # type: ignore
    value = None
    while True:
        value = input(
            f"\"{query_param_name}\" ({str(query_param_type).replace('<class ', '').replace('>', '')}) : "
        )
        # TODO: process bool and int
        if type(value) is query_param_type or not value:
            return value


def _query_params(query_params_type: dict) -> dict:
    query_params_data = {}
    print()
    print("".center(80, "-"))
    resp = input("Do you want to add a query_param (y/N)? ")
    if resp.lower() == "y":
        i = 0
        query_params_list = []
        for query_param in query_params_type:
            query_params_list.append(query_param)
            print(f"{i}) {query_param}={query_params_data.get(query_param, 'Not set')}")
            i += 1
        while resp.lower() != "x":
            index = None
            print()
            resp = input(
                f'Please select a query_param to add to the request (0-{i-1}, "r" to reset the query_params, or "x" to finish): '
            )
            if resp.lower() == "r":
                query_params_data = {}
            elif resp.lower() != "x":
                try:
                    index = int(resp)
                    if index < 0 or index > i - 1:
                        console.error(
                            "Please enter a number between 0 and {i-1}, or x to finish.\r\n"
                        )
                    else:
                        query_param_name = query_params_list[index]
                        value = _query_param_input(
                            query_param_name, query_params_type[query_param_name]
                        )
                        if value:
                            query_params_data[query_param_name] = value
                except:
                    console.error("Please enter a number.\r\n")

        return query_params_data
    else:
        return query_params_data


########################################################################
#### COMMON FUNCTIONS ####


def _searchDeviceEvents(
    apisession: mistapi.APISession,
    org_id: str,
    query_params: dict | None = None,
):
    query_params_type = {
        "device_type": str,
        "mac": str,
        "model": str,
        "text": str,
        "type": str,
        "duration": str,
        "limit": int,
    }

    if not query_params:
        query_params = _query_params(query_params_type)
    return mistapi.api.v1.orgs.devices.searchOrgDeviceEvents(
        apisession,
        org_id,
        mac=query_params.get("mac"),
        model=query_params.get("model"),
        text=query_params.get("text"),
        type=query_params.get("type"),
        device_type=query_params.get("device_type"),
        duration=query_params.get("duration", "1d"),
        limit=query_params.get("limit", 1000),
    )


def _searchSites(apisession: mistapi.APISession, org_id: str):

    resp = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id)
    data = mistapi.get_all(apisession, resp)
    return data


def _gen_summary(host: str, org_id: str, data: dict, sites: dict):
    sites_map = {}
    sites_done = []
    output = []
    for site in sites:
        sites_map[site["id"]] = site
    for e in data:
        if e.get("site_id") and e.get("site_id") not in sites_done:
            sites_done.append(e.get("site_id"))
            site = sites_map.get(e["site_id"])
            if site:
                output.append(
                    {
                        "site": site.get("name"),
                        "link": f"https://{host.replace('api', 'manage')}/admin/?org_id={org_id}#!dashboard/insights/{site.get('id')}",
                    }
                )
    return output


####################
## PROGRESS BAR
def _progress_bar_update(count: int, total: int, size: int):
    if total == 0:
        return
    elif count > total:
        count = total
    x = int(size * count / total)
    out.write(f"Progress: ".ljust(10))
    out.write(f"[{'█'*x}{'.'*(size-x)}]")
    out.write(f"{count}/{total}\r".rjust(19))
    out.flush()


def _progress_bar_end(total: int, size: int):
    if total == 0:
        return
    _progress_bar_update(total, total, size)
    out.write("\n")
    out.flush()


####################
## REQUEST
def _process_request(
    apisession: mistapi.APISession,
    scope_id: str,
    query_params: dict | None = None,
):
    data = []
    start = None
    end = None

    print(" Retrieving Data from Mist ".center(80, "-"))
    print()

    # First request to get the number of entries
    response = _searchDeviceEvents(apisession, scope_id, query_params)
    start = response.data.get("start", "N/A")
    end = response.data.get("end", "N/A")
    data = data + response.data["results"]

    # Variables and function for the progress bar
    size = 50
    i = 1
    total = response.data["total"]
    limit = response.data["limit"]
    if total:
        _progress_bar_update(i * limit, total, size)

        # request the rest of the data
        while response.next:
            response = mistapi.get_next(apisession, response)
            data = data + response.data["results"]
            i += 1
            _progress_bar_update(i * limit, total, size)
        # end the progress bar
        _progress_bar_end(total, size)
        print()
        return start, end, data
    else:
        console.warning("There is no results for this search...")
        sys.exit(0)


####################
## SAVE TO FILE
def _save_as_csv(start: float, end: float, query_params: dict, data: list, prefix: str, timestamp: bool):
    headers = []
    size = 50
    total = len(data)
    print(" Saving Data ".center(80, "-"))
    print()
    print("Generating CSV Headers ".ljust(80, "."))
    i = 0
    for entry in data:
        for key in entry:
            if not key in headers:
                headers.append(key)
        i += 1
        _progress_bar_update(i, total, size)
    _progress_bar_end(total, size)
    print()
    print("Saving report to file ".ljust(80, "."))
    i = 0
    if timestamp:
        backup_name = (f"{prefix}_report_{round(datetime.datetime.timestamp(datetime.datetime.now()))}.csv")
    else:
        backup_name = (f"{prefix}_report.csv")
    with open(backup_name, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(
            [
                f"Params: {query_params}",
                f"start: {start}",
                f"end:{end}",
            ]
        )
        csv_writer.writerow(headers)
        for entry in data:
            tmp = []
            for header in headers:
                tmp.append(entry.get(header, ""))
            csv_writer.writerow(tmp)
            i += 1
            _progress_bar_update(i, total, size)
        _progress_bar_end(total, size)


def _save_summary(start: float, end: float, query_params: dict, summary: list, prefix: str, timestamp: bool):
    headers = ["site", "link"]
    print("Saving summary to file ".ljust(80, "."))
    if timestamp:
        backup_name = (f"{prefix}_summary_{round(datetime.datetime.timestamp(datetime.datetime.now()))}.csv")
    else:
        backup_name = (f"{prefix}_summary.csv")
    with open(backup_name, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(
            [
                f"Params: {query_params}",
                f"start: {start}",
                f"end:{end}",
            ]
        )
        csv_writer.writerow(headers)
        for entry in summary:
            csv_writer.writerow([entry.get("site"), entry.get("link")])
        print()


def start(
    apisession: mistapi.APISession,
    org_id: str | None = None,
    query_params: dict | None = None,
    prefix: str = "org_events",
    timestamp: bool = False,
):
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    start, end, data = _process_request(apisession, org_id, query_params)
    sites = _searchSites(apisession, org_id)
    _save_as_csv(start, end, query_params, data, prefix, timestamp)
    summary = _gen_summary(apisession.get_cloud(), org_id, data, sites)
    _save_summary(start, end, query_params, summary, prefix, timestamp)


def usage(message: str = None):
    """Function to display Help"""
    print(
        f"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------

Python script to export historical device events from Mist API and save the result 
and a summary in CSV files.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Options:
-h, --help          display this help
-o, --org_id=       required for Org reports. Set the org_id    
-q, --q_params=     list of query parameters. Please see the possible filters
                    in https://doc.mist-lab.fr
                    format: -q key1:value1 -q key2:value2 -q ...

-p, --prefix=       define the prefix of the output files. Two files will be genereated:
                    <prefix>_report.csv: list all the events
                    <prefix>_summary.csv: list all the sites (with the dashboad URL)
                    default is "org_events"
-t, --timestamp     append the timestamp at the end of the report and summary files

-l, --log_file=     define the filepath/filename where to write the logs
                    default is {LOG_FILE}
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is {ENV_FILE}

-------
Examples:
python3 ./export_search.py                  
python3 ./export_searchs.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --report=client_sessions_wireless --q_params=duration:1w  
    """
    )
    if message:
        console.error(message)
    sys.exit(0)


def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        logger.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:p:e:l:q:t",
            [
                "help",
                "org_id=",
                "prefix=",
                "env=",
                "log_file=",
                "q_params=",
                "timestamp",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    QUERY_PARAMS = {}
    TIMESTAMP = False
    FILE_PREFIX = "org_events"
    for o, a in opts:  # type: ignore
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--prefix"]:
            FILE_PREFIX = a
        elif o in ["-t", "--timestamp"]:
            TIMESTAMP = True
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-q", "--q_params"]:
            if a.count(":") != 1:
                usage(f"Unable to process param {a}")
            else:
                QUERY_PARAMS[a.split(":")[0]] = a.split(":")[1]
            print(QUERY_PARAMS)
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    start(apisession, ORG_ID, QUERY_PARAMS, FILE_PREFIX, TIMESTAMP)