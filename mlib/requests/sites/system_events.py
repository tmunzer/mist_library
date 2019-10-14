

def get_definition(mist_session):
    uri = "/api/v1/const/system_events"
    resp = mist_session.mist_get(uri)
    return resp
def search(mist_session, site_id, mtype, start, end):
    uri = "/api/v1/sites/%s/events/system/search?type=%s&start=%s&end=%s" % (site_id, mtype, start, end)
    resp = mist_session.mist_get(uri)
    return resp
def count(mist_session, site_id, mtype, start, end):
    uri = "/api/v1/sites/%s/events/system/count?type=%s&start=%s&end=%s" % (site_id, mtype, start, end)
    resp = mist_session.mist_get(uri)
    return resp
