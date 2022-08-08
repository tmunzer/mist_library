
def get_client_events_definitions(mist_session):
    uri = "/api/v1/const/client_events"
    resp = mist_session.mist_get(uri)
    return resp

def get_device_events_definitions(mist_session):
    uri = "/api/v1/const/device_events"
    resp = mist_session.mist_get(uri)
    return resp

def get_mxedge_events_definitions(mist_session):
    uri = "/api/v1/const/mxedge_events"
    resp = mist_session.mist_get(uri)
    return resp


