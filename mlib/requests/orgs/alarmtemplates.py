def create(mist_session, org_id, alarmtemplate_settings):
    uri = f"/api/v1/orgs/{org_id}/alarmtemplates" 
    body = alarmtemplate_settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, alarmtemplate_settings, body={}):
    uri = f"/api/v1/orgs/{org_id}/alarmtemplates/{alarmtemplate_settings}" 
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
    
def delete(mist_session, org_id, alarmtemplate_settings):
    uri = f"/api/v1/orgs/{org_id}/alarmtemplates/{alarmtemplate_settings}" 
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/alarmtemplates" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def get_by_id(mist_session, org_id, alarmtemplate_id):
    uri = f"/api/v1/orgs/{org_id}/alarmtemplates/{alarmtemplate_id}" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp


