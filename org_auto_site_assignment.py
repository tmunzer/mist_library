'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### PARAMETERS #####

auto_site_assignment = {
    "enable": True,
    "rules": []
}

#### IMPORTS #####
import mlib as mist_lib
from mlib import cli
from tabulate import tabulate

#### GLOBAL VARIABLES ####
auto_assignment_rules = ["name", "subnet", "lldp_system_name", "dns_suffix", "model" ]

#### FUNCTIONS ####
def create_rule():
    rule_conf = {}
    while True:
        rule_conf = select_rule_type()
        cli.display_json(rule_conf)
        resp = input("Is it correct (Y/n)?")
        if resp.lower() == 'y' or resp == "":
            auto_site_assignment["rules"].append(rule_conf)
            break

def select_rule_type():
    rule_conf = {}
    while True:
        print("Type of auto assignement rule:")
        i = -1
        for rule in auto_assignment_rules:
            i+=1
            print("%s) %s" %(i, rule))
        resp = input("Please select the type of rule (0-%s)" %i)
        try:
            resp_num = int(resp)
            if resp_num >= 0 and resp_num <= i:
                rule_conf['src'] = auto_assignment_rules[resp_num]
                return configure_rule(rule_conf)
            else:
                print("Error: %s is not authorized" % resp_num)
        except:
            print("Error. The value %s is not valid" % resp)


def configure_rule(rule_conf):
    if rule_conf['src'] == "name":
        # // use device name (via Installer APIs)
        #{
        #     "src": "name",
        #     "expression": "[0:3]",           // "abcdef" -> "abc"
        #                   "split(.)[1]",     // "a.b.c" -> "b"
        #                   "split(-)[1][0:3], // "a1234-b5678-c90" -> "b56"  
        #     "prefix": "XX-",
        #     "suffix": "-YY"
        # },             
        print("Expression to extract the site name from the LLDP system name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
        rule_conf['prefix'] = input("Prefix (XX-): " )
        rule_conf['suffix'] = input("Suffix (-XX): ")
    elif rule_conf['src'] == "subnet":
        # // use subnet
        # {
        #     "src": "subnet",
        #     "subnet": "10.1.2.0/18",
        #     "value": "s1351"
        # },
        rule_conf['subnet'] = input("Please enter the subnet value (ex: 10.1.2.0/18): ")
        site_id = cli.select_site(mist, org_id=org_id)
        rule_conf['value'] = mist_lib.requests.orgs.sites.stats(mist, site_id)['result']['name']             
    elif rule_conf['src'] == "lldp_system_name":
        # // use LLDP System Name
        # {
        #     "src": "lldp_system_name",
        #     "expression": "..." // same as above
        # },
        print("Expression to extract the site name from the LLDP system name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
    elif rule_conf['src'] == "dns_suffix":
        # // use DNS Suffix
        # {
        #     "src": "dns_suffix",
        #     "expression": "..." // same as above
        # },
        print("Expression to extract the site name from the DNS suffix name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
    elif rule_conf['src'] == "model":
        # {
        #     "src": "model",
        #     "model": "AP41",
        #     "value": "s1351"
        # }       
        rule_conf['model'] = input("Please enter the model of AP: ")
        site_id = cli.select_site(mist, org_id=org_id)
        rule_conf['value'] = mist_lib.requests.orgs.sites.stats(mist, site_id)['result']['name'] 
    return rule_conf


####### ENTRY POINT #######


mist = mist_lib.Mist_Session()
org_id = cli.select_org(mist)

while True:
    resp = input("Do you want to enable auto site assignement (Y/n)?")
    if resp.lower() == 'y' or resp == "":
        auto_site_assignment["enable"] = True
        break
    else:
        auto_site_assignment["enable"] = False
        break

if auto_site_assignment["enable"] == True:
    auto_site_assignment["rules"].append(create_rule())


cli.display_json(auto_site_assignment)


mist_lib.requests.orgs.settings.update(mist, org_id, {"auto_site_assignment": auto_site_assignment})
cli.display_json(mist_lib.requests.orgs.settings.get(mist, org_id)["result"])
