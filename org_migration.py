import mlib as mist_lib
from mlib import cli

import org_conf_backup
import org_conf_restore
import org_inventory_backup
import org_inventory_backup
import org_inventory_precheck
import org_inventory_restore

def _connect(mist_session=None):
    host = cli.select_cloud()
    if not mist_session or not mist_session.host == host:
        mist_session = mist_lib.Mist_Session(host=host)
        return mist_session

def _backup_org():
    print("""
###################################################
## Backuping the source orgnization
###################################################
""")
    source_mist_session = _connect()
    source_org_id = cli.select_org(source_mist_session)
    source_org_name = mist_lib.orgs.info.get(source_mist_session, source_org_id)["result"]["name"]
    org_conf_backup.start_org_backup(source_mist_session, source_org_id, source_org_name)
    return (source_mist_session, source_org_id, source_org_name)

def _restore_org(source_mist_session, source_org_name):
    print("""
###################################################
## Restoring to the destination orgnization
###################################################
""")
    destination_mist_session = _connect(source_mist_session)
    dest_org_id = cli.select_org(destination_mist_session)
    dest_org_name = mist_lib.orgs.info.get(destination_mist_session, source_org_id)["result"]["name"]
    org_conf_restore.start_restore_org(destination_mist_session, dest_org_id, dest_org_name, source_org_name)
    return (destination_mist_session, dest_org_id, dest_org_name)

#######
#######

def _backup_inventory(source_mist_session, source_org_id, source_org_name):
    print("""
###################################################
## Backuping the source inventory
###################################################
""")    
    org_inventory_backup.start_inventory_backup(source_mist_session, source_org_id, source_org_name)
    org_conf_backup.start_org_backup(source_mist_session, source_org_id, source_org_name)
    return (source_mist_session, source_org_id, source_org_name)

def _precheck_inventory(dest_mist_session, dest_org_id, dest_org_name):
    print("""
###################################################
## Pre-check for inventory restoration
##  to the destination orgnization
###################################################
""")
    res = org_inventory_precheck(dest_mist_session, dest_org_id, dest_org_name)
    return (res)

def _restore_inventory(source_mist_session):
    print("""
###################################################
## Restoring to the destination orgnization
###################################################
""")
    destination_mist_session = _connect(source_mist_session)
    dest_org_id = cli.select_org(mist_session)
    dest_org_name = mist_lib.orgs.info.get(mist_session, source_org_id)["result"]["name"]
    org_conf_restore.start(destination_mist_session)
    return (destination_mist_session, dest_org_id, dest_org_name)


def _do_next_step(step):    
    do_next = None
    while not do_next :
        response = input("Do you want to %s (y/N)? " %(step))
        if response.lower() == "y":
            do_next = True
        if respones.lower == "n" or response == "":
            do_next = False
    return do_next
        

if __name__ == "__main__":
    source_mist_session = None
    if _do_next_step("backup an existing orgnanization"):
        source_mist_session, source_org_id, source_org_name = _backup_org()
    if _do_next_step("restore the backup to a new orgnanization"):
        dest_mist_session, dest_org_id, dest_org_name = _restore_org(source_org_name)
    if _do_next_step("backup the inventory from the source orgnanization"):
        precheck = _precheck_inventory(dest_mist_session, dest_org_id, dest_org_name, source_org_name)
