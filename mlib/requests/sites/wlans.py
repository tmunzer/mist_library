
def get(mist_session, site_id, page=1, limit=100):
    uri = "/api/v1/sites/%s/wlans" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id, page=page, limit=limit)
    return resp


def create(mist_session, site_id, wlan_settings):
    uri = "/api/v1/sites/%s/wlans" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=wlan_settings)
    return resp

def delete(mist_session, site_id, wlan_id):
    uri = "/api/v1/sites/%s/wlans/%s" % (site_id, wlan_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp


def add_portal_image(mist_session, site_id, wlan_id, image_path):
    uri = "/api/v1/sites/%s/wlans/%s/portal_image" %(site_id, wlan_id)
    files = {'file': open(image_path, 'rb').read()}
    resp = mist_session.mist_post_file(uri, site_id=site_id, files=files)
    return resp

def delete_portal_image(mist_session, site_id, wlan_id):
    uri = "/api/v1/sites/%s/wlans/%s/portal_image" %(site_id, wlan_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp

def set_portal_template(mist_session, site_id, wlan_id, portal_template_body):
    uri = "/api/v1/sites/%s/wlans/%s/portal_template" %(site_id, wlan_id)
    body = portal_template_body
    resp = mist_session.mist_put(uri, site_id=site_id, body=body)
    return resp

    
def report(mist_session, site_id, fields):
    wlans = get(mist_session, site_id)
    result = []
    for wlan in wlans['result']:
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
        result.append(temp)
    return result
