'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

This script will import PSKs from a CSV file to one or multiple sites.
Usage:
python3 site_conf_psk_import_csv.py path_to_the_csv_file.csv

CSV file format:

pskName1,pskValue1,Wlan1
pskName2,pskValue2,Wlan2

'''
#### PARAMETERS #####
csv_separator = ","

#### IMPORTS #####
import mlib as mist_lib
from mlib import cli
from tabulate import tabulate
import sys
import csv


#### FUNCTIONS #####

def import_psk(site_id, psks):
    print("")
    print("________________________________________")
    print("Starting PSKs import for site %s" %(site_id))
    for psk in psks:     
        print('PSK %s' %(psk["username"]))
        pskObj = mist_lib.models.sites.psks.Psk()
        pskObj.define(name=psk["username"], passphrase=psk["passphrase"], ssid=psk["ssid"])
        mist_lib.requests.sites.psks.create(mist, site_id, pskObj.toJSON())
        print(pskObj.toJSON())

def read_csv(csv_file): 
    print("")   
    print("________________________________________")
    print("Opening CSV file %s" %(csv_file))
    psks = []
    try:
        with open(sys.argv[1], 'r') as my_file:
            ppsk_file = csv.reader(my_file, delimiter=',')
            for row in ppsk_file:
                username = row[0]
                passphrase = row[1]
                ssid = row[2]
                psks.append({"username": username,"passphrase": passphrase,"ssid": ssid})    
        return psks 
    except:
        print("Error while opening the CSV file... Aborting")

def list_psks(site_id):
    print("")
    print("________________________________________")
    print("List of current PSKs for site %s" %(site_id))
    psks = mist_lib.requests.sites.psks.get(mist, site_id)['result']
    cli.show(psks)

#### SCRIPT ENTRYPOINT #####

mist = mist_lib.Mist_Session()
site_ids = cli.select_site(mist, allow_many=True)
print("__________________")
print(site_ids)

psks = read_csv(sys.argv[1])

for site_id in site_ids:
    import_psk(site_id, psks)

for site_id in site_ids:
    list_psks(site_id)