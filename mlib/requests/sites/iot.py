
def get(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/devices/%s/iot" % (site_id, device_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp


def set(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/devices/%s/iot" % (site_id, device_id)
    resp = mist_session.mist_put(uri, site_id=site_id)
    return resp
