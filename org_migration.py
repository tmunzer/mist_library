'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import mlib as mist_lib
from mlib import cli

import org_conf_backup
import org_conf_deploy
import org_inventory_backup
import org_inventory_backup
import org_inventory_precheck
import org_inventory_restore




def _backup_org(source_mist_session, source_org_id, source_org_name):
    _print_new_step("Backuping the CONFIGURATION\n## from the SOURCE organization")
    org_conf_backup.start_org_backup(source_mist_session, source_org_id, source_org_name)    

def _restore_org(dest_mist_session, dest_org_id, dest_org_name, source_org_name, check_org_name=False, in_backup_folder=False):
    _print_new_step("Restoring the CONFIGURATION\n## to the DESTINATION organisation")
    org_conf_restore.start_restore_org(dest_mist_session, dest_org_id, dest_org_name, source_org_name, check_org_name, in_backup_folder)

#######
#######

def _backup_inventory(source_mist_session, source_org_id, source_org_name, in_backup_folder=False):
    _print_new_step("Backuping the INVENTORY\n## from the SOURCE organization")
    org_inventory_backup.start_inventory_backup(source_mist_session, source_org_id, source_org_name, in_backup_folder)

def _precheck_inventory(dest_mist_session, dest_org_id, dest_org_name, source_org_name, in_backup_folder=False):
    _print_new_step("Pre-check for INVENTORY restoration\n## to the destination orgnization")
    org_inventory_precheck.start_precheck(dest_mist_session, dest_org_id, dest_org_name,source_org_name, None, in_backup_folder)

def _restore_inventory(dest_mist_session, dest_org_id, dest_org_name, source_mist_session, source_org_name, source_org_id, check_org_name=False, in_backup_folder=False):
    _print_new_step("Restoring the INVENTORY\n## to the DESTINATION organisation")
    org_inventory_restore.start_restore_inventory(dest_mist_session, dest_org_id, dest_org_name, source_mist_session, source_org_name, source_org_id, None, check_org_name, in_backup_folder)

#######
#######

def _print_new_step(message):
    print("""
###################################################
## %s
###################################################
""" %(message))



def _select_org(mist_session=None, host=None):
    mist_session = mist_lib.Mist_Session(host=host)    
    org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    return (mist_session, org_id, org_name)

if __name__ == "__main__":
    _print_new_step("Please select the SOURCE organization")
    source_mist_session, source_org_id, source_org_name = _select_org()
    _print_new_step("Please select the DESTINATION organization")
    dest_mist_session, dest_org_id, dest_org_name = _select_org()

    _backup_org(source_mist_session, source_org_id, source_org_name)
    _backup_inventory(source_mist_session, source_org_id, source_org_name, in_backup_folder=True)
    _restore_org(dest_mist_session, dest_org_id, dest_org_name, source_org_name, in_backup_folder=True)
    _precheck_inventory(dest_mist_session, dest_org_id, dest_org_name, source_org_name, in_backup_folder=True)
    _restore_inventory(dest_mist_session, dest_org_id, dest_org_name, source_mist_session, source_org_name, source_org_id, in_backup_folder=True)
    
