
def get_definition(mist_session):
    uri = "/api/v1/const/client_events"
    resp = mist_session.mist_get(uri)
    return resp
