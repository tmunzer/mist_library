########## ADMINS ############

def get(mist_session, org_id):
    uri = "/api/v1/orgs/%s/admins" % org_id
    resp = mist_session.mist_get(uri, org_id=org_id)
    return resp

def update(mist_session, org_id, admin_id, privileges=""):
    uri = "/api/v1/orgs/%s/admins/%s" % (org_id, admin_id)
    body = {}
    if privileges != "":
        body["privileges"] = privileges
    resp = mist_session.mist_put(uri, org_id=org_id, body=body)
    return resp

def revoke(mist_session, org_id, admin_id):
    uri = "/api/v1/orgs/%s/admins/%s" %(org_id, admin_id)
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def create_invite(mist_session, org_id, email, privileges, first_name = "", last_name = "", hours = 24):
    uri =   "/api/v1/orgs/%s/invites" % org_id
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
    uri = "/api/v1/orgs/%s/invites/%s" % (org_id, invite_id)
    resp = mist_session.mist_delete(uri, org_id=org_id)
    return resp

def update_invite(mist_session, org_id, invite_id, email = "", privileges = "", first_name = "", last_name = "", hours = ""):
    uri = "/api/v1/orgs/%s/invites/%s" % (org_id, invite_id)
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


