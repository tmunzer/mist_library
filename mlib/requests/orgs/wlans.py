from . import templates

def get(mist_session, org_id, page=1, limit=100):
    uri = "/api/v1/orgs/%s/wlans" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp


def create(mist_session, org_id, wlan_settings):
    uri = "/api/v1/orgs/%s/wlans" % org_id
    resp = mist_session.mist_post(uri, org_id=org_id, body=wlan_settings)
    return resp

def delete(mist_session, org_id, wlan_id):
    uri = "/api/v1/orgs/%s/wlans/%s" % (org_id, wlan_id)
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp


def report(mist_session, org_id, fields):
    wlans = get(mist_session, org_id)
    
    result = []
    for wlan in wlans['result']:
        template = templates.get_details(mist_session, org_id, wlan["template_id"])['result']
        if "applies" in template and "site_ids" in template["applies"]:
            temp = []
            for field in fields:
                if field not in wlan:
                    temp.append("")
                elif field == "auth":
                    temp.append(str(wlan["auth"]["type"]))
                elif field == "auth_servers":
                    string = ""
                    for server_num, server_val in enumerate(wlan["auth_servers"]):
                        if "host" in server_val:
                            string += "%s:%s" % (server_val["host"],
                                                server_val["port"])
                        else:
                            string += "%s:%s" % (server_val["ip"],
                                                server_val["port"])
                        if server_num < len(wlan["auth_servers"]) - 1:
                            string += " - "
                    temp.append(string)
                elif field == "acct_servers":
                    string = ""
                    for server_num, server_val in enumerate(wlan["auth_servers"]):
                        if "host" in server_val:
                            string += "%s:%s" % (server_val["host"],
                                                server_val["port"])
                        else:
                            string += "%s:%s" % (server_val["ip"],
                                                server_val["port"])
                        if server_num < len(wlan["acct_servers"]) - 1:
                            string += " - "
                    temp.append(string)
                elif field == "dynamic_vlan":
                    string = "Disabled"
                    if wlan["dynamic_vlan"] != None and wlan["dynamic_vlan"]["enabled"] == True:
                        string = "default: "
                        if "default_vlan_id" in wlan["dynamic_vlan"]:
                            string += "%s | others: " % wlan["dynamic_vlan"]["default_vlan_id"]
                        else:
                            string += "N/A | others: "
                        if wlan["dynamic_vlan"]["vlans"] != None:
                            for vlan_num, vlan_val in enumerate(wlan["dynamic_vlan"]["vlans"]):
                                string += "%s" % vlan_val
                                if vlan_num < len(wlan["dynamic_vlan"]["vlans"]) - 1:
                                    string += " - "
                        else:
                            string += "None"
                    temp.append(string)
                else:
                    temp.append("%s" % wlan[field])
            
            for site_id in template["applies"]["site_ids"]:                        
                    result.append([ site_id ] + temp)
    return result
