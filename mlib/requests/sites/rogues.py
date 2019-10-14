

def set_rogue(mist_session, site_id, rogue_param):
    uri = "/api/v1/sites/%s/setting" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=rogue_param)
    return resp
