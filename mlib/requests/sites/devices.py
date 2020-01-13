
def get(mist_session, site_id, name=""):
    uri = "/api/v1/sites/%s/devices" % site_id
    if name != "":
        uri += "?name=%s" % name
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def get_details(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/devices/%s" % (site_id, device_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def get_stats_devices(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/stats/devices/%s" % (site_id, device_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def create(mist_session, site_id, devices):
    uri = "/api/v1/sites/%s/devices" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=devices)
    return resp


def update(mist_session, site_id, device_id, device_settings):
    uri = "/api/v1/sites/%s/devices/%s" % (site_id, device_id)
    resp = mist_session.mist_put(uri, site_id=site_id, body=device_settings)
    return resp


def delete(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/devices/%s" % (site_id, device_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp
