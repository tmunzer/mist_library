
def create(mist_session, org):
    uri = "/api/v1/orgs"
    resp = mist_session.mist_post(uri, org_id=None, body=org)
    return resp


def get(mist_session, org_id, psk_id="", name="", ssid="", page=1, limit=100):
    uri = "/api/v1/orgs/%s/psks" % org_id
    query={}
    if psk_id != "":
        uri +="/%s" % psk_id
    if name != "":
        query["name"] = name
    if  ssid != "":
        query["ssid"] = ssid
    resp = mist_session.mist_get(uri, org_id=org_id, query=query, page=page, limit=limit)
    return resp 

def delete(mist_session, org_id, psk_id="", name="", ssid=""):
    uri = "/api/v1/orgs/%s/psks" % org_id
    if psk_id != "":
        uri +="/%s" % psk_id
    if org_id != "" and ssid != "":
        uri += "?name=%s&ssid=%s" % (name, ssid)
    elif name != "":
        uri += "?name=%s" % name
    elif  ssid != "":
        uri += "?ssid=%s" % ssid
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp 
