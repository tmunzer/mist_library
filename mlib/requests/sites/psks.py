

def add(mist_session, site_id, ssid, passphrase):
    uri = "/api/v1/sites/%s/psks" % site_id
    body = {
        "ssid": ssid,
        "passphrase": passphrase
    }
    resp = mist_session.mist_post(uri, site_id=site_id, body=body)
    return resp

def get(mist_session, site_id, name="", ssid=""):
    uri = "/api/v1/sites/%s/psks" % site_id
    if site_id != "":
        uri += "?name=%s" % name
    elif  ssid != "":
        uri += "?ssid=%s" % ssid
    elif site_id != "" and ssid != "":
        uri += "?name=%s&ssid=%s" % (name, ssid)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp 

def delete(mist_session, site_id, name="", ssid=""):
    uri = "/api/v1/sites/%s/psks" % site_id
    if site_id != "":
        uri += "?name=%s" % name
    elif  ssid != "":
        uri += "?ssid=%s" % ssid
    elif site_id != "" and ssid != "":
        uri += "?name=%s&ssid=%s" % (name, ssid)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp 
