from . import templates

def get(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/wlans" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def get_by_id(mist_session, org_id, wlan_id):
    uri = f"/api/v1/orgs/{org_id}/wlans/{wlan_id}" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def create(mist_session, org_id, wlan_settings):
    uri = f"/api/v1/orgs/{org_id}/wlans" 
    resp = mist_session.mist_post(uri, org_id=org_id, body=wlan_settings)
    return resp

def delete(mist_session, org_id, wlan_id):
    uri = f"/api/v1/orgs/{org_id}/wlans/{wlan_id}" 
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def add_portal_image(mist_session, org_id, wlan_id, image_path):
    uri = f"/api/v1/orgs/{org_id}/wlans/{wlan_id}/portal_image" 
    f = open(image_path, 'rb')
    files = {'file': f.read()}
    resp = mist_session.mist_post_file(uri, org_id=org_id, files=files)
    f.close()
    return resp

def delete_portal_image(mist_session, org_id, wlan_id):
    uri = f"/api/v1/orgs/{org_id}/wlans/{wlan_id}/portal_image" 
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def set_portal_template(mist_session, org_id, wlan_id, portal_template_body):
    uri = f"/api/v1/orgs/{org_id}/wlans/{wlan_id}/portal_template" 
    body = portal_template_body
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
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
                            string += f"{server_val['host']}:{server_val['port']}"
                        else:
                            string += f"{server_val['ip']}:{server_val['port']}"
                        if server_num < len(wlan["auth_servers"]) - 1:
                            string += " - "
                    temp.append(string)
                elif field == "acct_servers":
                    string = ""
                    for server_num, server_val in enumerate(wlan["auth_servers"]):
                        if "host" in server_val:
                            string += f"{server_val['host']}:{server_val['port']}"
                        else:
                            string += f"{server_val['ip']}:{server_val['port']}"
                        if server_num < len(wlan["acct_servers"]) - 1:
                            string += " - "
                    temp.append(string)
                elif field == "dynamic_vlan":
                    string = "Disabled"
                    dynamic_vlan = wlan.get("dynamic_vlan", {"enabled": False})
                    if dynamic_vlan and dynamic_vlan.get("enabled", False) == True:
                        string = "default: "
                        if "default_vlan_id" in wlan["dynamic_vlan"]:
                            string += f"{wlan['dynamic_vlan']['default_vlan_id']} | others: " 
                        else:
                            string += "N/A | others: "
                        if wlan["dynamic_vlan"]["vlans"]:
                            for vlan_num, vlan_val in enumerate(wlan["dynamic_vlan"]["vlans"]):
                                string += f"{vlan_val}" 
                                if vlan_num < len(wlan["dynamic_vlan"]["vlans"]) - 1:
                                    string += " - "
                        else:
                            string += "None"
                    temp.append(string)
                else:
                    temp.append(f"{wlan[field]}")
            
            for site_id in template["applies"]["site_ids"]:                        
                    result.append([ site_id ] + temp)
    return result
