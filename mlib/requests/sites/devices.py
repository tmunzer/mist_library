
def get(mist_session, site_id, name=None, device_type=None, page=1, limit=100):
    uri = "/api/v1/sites/%s/devices" % site_id
    query={}
    if name:
        query[name] = name
    if device_type:
        query["type"] = device_type
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp

def get_details(mist_session, site_id, device_id):
    uri = "/api/v1/sites/%s/devices/%s" % (site_id, device_id)
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def get_stats_devices(mist_session, site_id, device_id=None, device_type=None, page=1, limit=100):
    uri = "/api/v1/sites/%s/stats/devices" % site_id
    query={}
    if device_id:
        uri += "/%s" %device_id
    if device_type:
        query["type"] = device_type
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
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

def add_image(mist_session, site_id, device_id, image_num, image_path):
    uri = "/api/v1/sites/%s/devices/%s/image%s" %(site_id, device_id, image_num)
    files = {'file': open(image_path, 'rb').read()}
    resp = mist_session.mist_post_file(uri, site_id=site_id, files=files)
    return resp

def set_device_conf(mist_session, site_id, device_id, conf):
    uri = "/api/v1/sites/%s/devices/%s" %(site_id, device_id)
    body = conf
    resp = mist_session.mist_put(uri, site_id=site_id, body=body)
    return resp


