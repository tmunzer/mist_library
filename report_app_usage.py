'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### IMPORTS ####
import mlib as mist_lib
from mlib import cli
from mlib.__debug import Console
import csv
import datetime

console = Console(7)

hours_to_report = 96
csv_delimiter = ","
csv_file = "report_app_usage.csv"

def _get_clients_list(mist_session, site_id):
    clients = mist_lib.sites.stats.clients(mist_session, site_id)["result"]
    return clients


def _get_site_name(mist_session, site_id):
    site_info = mist_lib.sites.info.get(mist_session, site_id)["result"]
    return site_info["name"]

def _convert_numbers(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    size = round(size, 2)
    return "%s %sB" %(size, power_labels[n])

def _generate_site_report(mist_session, site_name, site_id, start, stop, interval):
    app_usage = []
    clients = _get_clients_list(mist_session, site_id)
    console.info("%s clients to process... Please wait..." %(len(clients)))
    for client in clients:
        client_mac = client["mac"]
        if "username" in client: client_username = client["username"]
        else: client_username = ""
        if "hostname" in client: client_hostname = client["hostname"]
        else: client_hostname = ""        
        client_app = mist_lib.sites.insights.client(mist_session, site_id, client_mac, start, stop, interval, "top-app-by-bytes")["result"]
        tmp={"site name": site_name, "site id": site_id, "client mac": client_mac, "username": client_username, "hostname": client_hostname}
        for app in client_app["top-app-by-bytes"]:
            usage = _convert_numbers(app["total_bytes"])
            tmp[app["app"]] = usage
        app_usage.append(tmp)
    return app_usage

def _save_report(app_usage):
    console.notice("Saving to file %s..." %(csv_file))
    fields = []
    for row in app_usage:
        for key in row:
            if not key in fields: fields.append(key)

    with open(csv_file, 'w') as output_file:
        dict_writer = csv.DictWriter(output_file, restval="-", fieldnames=fields, delimiter=csv_delimiter)
        dict_writer.writeheader()
        dict_writer.writerows(app_usage)
    console.notice("File %s saved!" %(csv_file))

def generate_report(mist_session, site_ids, time):
    app_usage = []
    if type(site_ids) == str:
        site_ids = [ site_ids]
    for site_id in site_ids:
        site_name = _get_site_name(mist_session, site_id)
        console.info("Processing site %s (id %s)" %(site_name, site_id))
        app_usage += _generate_site_report(mist_session, site_name, site_id, time["start"], time["stop"], time["interval"])
    cli.show(app_usage)
    _save_report(app_usage)

def _ask_period(hours):
    now = datetime.datetime.now()
    start = round((datetime.datetime.now() - datetime.timedelta(hours=hours)).timestamp(), 0)
    stop = round(now.timestamp(), 0)
    interval =  3600
    return {"start": start, "stop": stop, "interval": interval}


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session()
    site_id = cli.select_site(mist_session, allow_many=True)
    time = _ask_period(hours_to_report)
    generate_report(mist_session, site_id, time)
