def create(mist_session, org_id, webhook_settings):
    uri = f"/api/v1/orgs/{org_id}/webhooks" 
    body = webhook_settings
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def update(mist_session, org_id, webhook_id, body={}):
    uri = f"/api/v1/orgs/{org_id}/webhooks/{webhook_id}" 
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp
    
def delete(mist_session, org_id, webhook_id):
    uri = f"/api/v1/orgs/{org_id}/webhooks/{webhook_id}" 
    resp = mist_session.mist_delete(uri)
    return resp

def get(mist_session, org_id, page=1, limit=100):
    uri = f"/api/v1/orgs/{org_id}/webhooks" 
    resp = mist_session.mist_get(uri, org_id=org_id, page=page, limit=limit)
    return resp

def get_by_id(mist_session, org_id, webhook_id):
    uri = f"/api/v1/orgs/{org_id}/webhooks/{webhook_id}" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def report(mist_session, site_id, fields):
    webhooks = get(mist_session, site_id)
    result = []
    for webhook in webhooks['result']:
        temp = []
        for field in fields:
            if field not in webhook:
                temp.append("")
            elif field == "topics":
                temp.append(", ".join(webhook['topics']))            
            else:
                temp.append(f"{webhook[field]}")
        result.append(temp)
    return result
