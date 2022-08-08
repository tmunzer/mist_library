
def get_applications(mist_session):
    uri = "/api/v1/const/applications"
    resp = mist_session.mist_get(uri)
    return resp


