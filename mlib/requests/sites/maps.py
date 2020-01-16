def get(mist_session, site_id, page=1, limit=100):
    uri = "/api/v1/sites/%s/maps" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id, page=page, limit=limit)
    return resp

def delete(mist_session, site_id, map_id):
    uri = "/api/v1/sites/%s/maps/%s" %(site_id, map_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp

def create(mist_session, site_id, map_settings):
    uri = "/api/v1/sites/%s/maps" % site_id
    body = map_settings
    resp = mist_session.mist_post(uri, site_id=site_id, body=body)
    return resp


def add_image(mist_session, site_id, map_id, image_path):
    uri = "/api/v1/sites/%s/maps/%s/image" %(site_id, map_id)
    files = {'file': open(image_path, 'rb').read()}
    resp = mist_session.mist_post_file(uri, site_id=site_id, files=files)
    return resp

def delete_image(mist_session, site_id, map_id):
    uri = "/api/v1/sites/%s/maps/%s/image" %(site_id, map_id)
    resp = mist_session.mist_delete(uri, site_id=site_id)
    return resp