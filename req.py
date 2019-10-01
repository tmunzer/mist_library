import requests
import json


class Req:

    def __init__(self):
        self.host = ""
        self.session = requests.session()
        self.privileges = ""

    def _url(self, uri):
        """Generate the url with the host (in the object) and the uri
        Params: uri
        Return: url"""
        return "https://" + self.host + uri

    def _check_authorization(self, method, org_id="", site_id=""):
        if method in ["POST", "PUT", "DELETE"]:
            if org_id != "":
                for privilige in self.privileges:
                    if "org_id" in privilige and privilige['org_id'] == org_id:
                        if privilige["role"] in ["write", "admin"]:
                            return True
                print("authorization error")
                return False
            elif site_id != "":
                for privilige in self.privileges:
                    if "site_id" in privilige and privilige['site_id'] == site_id:
                        print(privilige)
                        if privilige["role"] in ["write", "admin"]:
                            return True
                print("authorization error")
                return False
        else:
            return True

    def _response(self, resp, uri=""):
        if resp.status_code == 200:
            result = resp.json()
            error = ""
        else:
            result = ""
            error = resp.json()
        # print(json.dumps(resp.json(), sort_keys=True,
        #                 indent=4, separators=(',', ': ')))
        return {"result": result, "status_code": resp.status_code, "error": error, "uri":uri}

    def mist_get(self, uri, org_id="", site_id="", query=""):
        """GET HTTP Request
        Params: uri, HTTP query
        Return: HTTP response"""
        if self._check_authorization("GET", org_id=org_id, site_id=site_id):
            headers = {
                'Content-Type': 'application/json'
            }
            resp = self.session.get(self._url(uri), headers=headers)
            return self._response(resp, uri)
        else:
            print("you're not authenticated yet...")

    def mist_post(self, uri, org_id="", site_id="", body={}):
        """POST HTTP Request
        Params: uri, HTTP body
        Return: HTTP response"""
        if self._check_authorization("POST", org_id=org_id, site_id=site_id):
            resp = self.session.post(self._url(uri), json=body)
            return self._response(resp, uri)
        else:
            print("you're not authenticated yet...")

    def mist_put(self, uri, org_id="", site_id="", body={}):
        """PUT HTTP Request
        Params: uri, HTTP body
        Return: HTTP response"""
        if self._check_authorization("PUT", org_id=org_id, site_id=site_id):
            resp = self.session.put(self._url(uri), json=body)
            return self._response(resp, uri)
        else:
            print("you're not authenticated yet...")

    def mist_delete(self, uri, org_id="", site_id=""):
        """DELETE HTTP Request
        Params: uri
        Return: HTTP response"""
        if self._check_authorization("PUT", org_id=org_id, site_id=site_id):
            resp = self.session.delete(self._url(uri))
            return self._response(resp, uri)
        else:
            print("you're not authenticated yet...")