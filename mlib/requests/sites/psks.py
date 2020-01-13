
def create(mist_session, site_id, psk):
    uri = "/api/v1/sites/%s/psks" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=psk)
    return resp


def get(mist_session, site_id, psk_id="", name="", ssid="", page=1, limit=100):
    uri = "/api/v1/sites/%s/psks" % site_id
    query={}
    if psk_id != "":
        uri +="/%s" % psk_id
    if name != "":
        query["name"] = name
    if  ssid != "":
        query["ssid"] = ssid
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp 

def delete(mist_session, site_id, psk_id="", name="", ssid=""):
    uri = "/api/v1/sites/%s/psks" % site_id
    if psk_id != "":
        uri +="/%s" % psk_id
    if site_id != "" and ssid != "":
        uri += "?name=%s&ssid=%s" % (name, ssid)
    elif name != "":
        uri += "?name=%s" % name
    elif  ssid != "":
        uri += "?ssid=%s" % ssid
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp 
