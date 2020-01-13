

def get_current_channel_planning(mist_session, site_id):
    uri = "/api/v1/sites/%s/rrm/current" % site_id
    resp = mist_session.mist_get(uri, site_id=site_id)
    return resp

def get_device_rrm_info(mist_session, site_id, device_id, band):
    uri = "/api/v1/sites/%s/rrm/current/devices/%s/band/%s" % (site_id, device_id, band)
    resp = mist_session.mist_get(uri,site_id=site_id)
    return resp

def optimize(mist_session, site_id, band_24=False, band_5=False):
    bands = []
    if band_24:
        bands.append("24")
    if band_5:
        bands.append("5")
    body = { "bands": bands}
    uri = "/api/v1/sites/%s/rrm/optimize" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id, body=body)
    return resp

def reset(mist_session, site_id):
    uri = "/api/v1/sites/%s/devices/reset_radio_config" % site_id
    resp = mist_session.mist_post(uri, site_id=site_id)
    return resp

def get_events(mist_session, site_id, band, duration="", page=1, limit=100):
    uri ="/api/v1/sites/%s/rrm/events?band=%s" % (site_id, band)
    query ={"band": band}
    if duration != "":
        query["duration"] = duration
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp

def get_interference_events(mist_session, site_id, duration="", page=1, limit=100):
    uri = "/api/v1/sites/%s/events/interference" %site_id
    query ={}
    if duration != "":
        query["duration"] = duration
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp

def get_roaming_events(mist_session, site_id, mtype, start="", end="", page=1, limit=100):
    uri = "/api/v1/sites/%s/events/fast_roam" %site_id
    query={"type": mtype}    
    if end != "":
        query["duration"]= end
    if limit != "":
        query["duration"]= limit
    resp = mist_session.mist_get(uri, site_id=site_id, query=query, page=page, limit=limit)
    return resp
