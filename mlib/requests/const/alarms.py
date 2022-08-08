
def get_alarm_definitions(mist_session):
    uri = "/api/v1/const/alarm_defs"
    resp = mist_session.mist_get(uri)
    return resp


