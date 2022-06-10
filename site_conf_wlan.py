'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import mlib as mist_lib
from mlib import cli
import json
import sys
from tabulate import tabulate
#### PARAMETERS #####
csv_separator = ","


def add_wlan():
    wlan_file = input("Path to the WLAN configuration JSON file (default: ./site_conf_wlan_settings.json): ")
    if wlan_file == "": 
        wlan_file = "./site_conf_wlan_settings.json"
    try:
        with open(wlan_file, "r") as f:
            wlan  = json.load(f)       
    except:
        print("Error while loading the configuration file... exiting...")
        sys.exit(255)
    try:
        wlan_json = json.dumps(wlan)
    except:
        print("Error while loading the wlan settings from the file... exiting...")
        sys.exit(255)
    mist_lib.requests.sites.wlans.create(mist, site_id, wlan_json)

def remove_wlan(site_id):
    wlans = mist_lib.requests.sites.wlans.get(mist, site_id)['result']
    resp = -1
    while True:    
        print()    
        print("Available WLANs:")
        i = -1
        for wlan in wlans:
            i+=1
            print("%s) %s (id: %s)" % (i, wlan["ssid"], wlan["id"]))        
        print()        
        resp = input("Which WLAN do you want to delete (0-%s, or q to quit)? " %i)
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= i:
                    wlan = wlans[resp_num]
                    print()    
                    confirmation = input("Are you sure you want to delete WLAN %s (y/N)? " % wlan["ssid"])
                    if confirmation.lower() == "y":
                        break
                else:
                    print("%s is not part of the possibilities." % resp_num)
            except:
                print("Only numbers are allowed.")
    mist_lib.requests.sites.wlans.delete(mist, site_id, wlan["id"])    


def display_wlan(site_id):
    fields = ["id","ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid"]
    site_wlans = mist_lib.requests.sites.wlans.report(mist, site_id, fields)   
    print(tabulate(site_wlans, fields))


mist = mist_lib.Mist_Session("./session.py")
#mist.save()
site_id = cli.select_site(mist, allow_many=False)

while True:
    print()    
    print(" ===================")
    print(" == CURRENT WLANS ==")
    display_wlan(site_id)
    print(" ===================")
    print()
    actions = ["add WLAN", "remove WLAN"]
    print("What do you want to do:")
    i = -1
    for action in actions:
        i+= 1
        print("%s) %s" % (i, action))
    print()    
    resp = input("Choice (0-%s, q to quit): " %i)
    if resp.lower() == "q":
        sys.exit(0)
    else:
        try:
            resp_num = int(resp)
            if resp_num >= 0 and resp_num <= len(actions):
                if actions[resp_num] == "add WLAN": 
                    add_wlan()
                    print()    
                    print(" ========================")
                    print(" == WLANS AFTER CHANGE ==")
                    display_wlan(site_id)
                    print(" ========================")              
                    break
                elif actions[resp_num] == "remove WLAN":
                    remove_wlan(site_id)
                    print()    
                    print(" ========================")
                    print(" == WLANS AFTER CHANGE ==")
                    display_wlan(site_id)
                    print(" ========================")
                    break
            else:
                print("%s is not part of the possibilities." % resp_num)
        except:
            print("Only numbers are allowed.")


