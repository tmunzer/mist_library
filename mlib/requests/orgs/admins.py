########## ADMINS ############

def get(mist_session, org_id):
    uri = f"/api/v1/orgs/{org_id}/admins" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def update(mist_session, org_id, admin_id, privileges=""):
    uri = f"/api/v1/orgs/{org_id}/admins/{admin_id}" 
    body = {}
    if privileges != "":
        body["privileges"] = privileges
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def get_by_id(mist_session, org_id, admin_id):
    uri = f"/api/v1/orgs/{org_id}/admins/{admin_id}" 
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def revoke(mist_session, org_id, admin_id):
    uri = f"/api/v1/orgs/{org_id}/admins/{admin_id}" 
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def create_invite(mist_session, org_id, email, privileges, first_name = "", last_name = "", hours = 24):
    uri =  f"/api/v1/orgs/{org_id}/invites" 
    body = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "hours": hours,
        "privileges": privileges
    }
    resp = mist_session.mist_post(uri, org_id=org_id, body=body)
    return resp

def delete_invite(mist_session, org_id, invite_id):
    uri = f"/api/v1/orgs/{org_id}/invites/{invite_id}" 
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def update_invite(mist_session, org_id, invite_id, email = "", privileges = "", first_name = "", last_name = "", hours = ""):
    uri = f"/api/v1/orgs/{org_id}/invites/{invite_id}" 
    body = {}
    if email != "":
        body["email"] = email
    if first_name != "":
        body["first_name"] = first_name
    if last_name != "":
        body["last_name"] = last_name
    if hours != "":
        body["hours"] = hours
    if privileges != "":
        body["privileges"] = privileges
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp


