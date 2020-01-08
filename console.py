import rlcompleter
import mlib
import mlib.cli as cli

session = mlib.Mist_Session()

def help():
    print('''
    Help:
    
    To start using this cli, you first have to create a Mist session and store it in a variable. It will be
    used with all the requests (as the first argument) to authenticate youserlf. To do so:
    --- 
    session = cli.mlib.Mist_Session()
    ---
    The you will be able to use the script to generate and send request to the Mist Cloud. For example, 
    you can do:

    ''')

def select_org_id():
    org_id = cli.select_org(session)
    print("")
    print("Selected org id: %s" %org_id)

def get_site_id():
    site_id = cli.select_site(session)
    print("Selected site id: %s" %site_id)


help()