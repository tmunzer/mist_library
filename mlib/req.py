import requests
from requests.exceptions import HTTPError

import json

try:
    from config import log_level
except:
    log_level = 6
finally:
    from .debug import Console
    console = Console(log_level)


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
                console.error("authorization error")
                return False
            elif site_id != "":
                for privilige in self.privileges:
                    if "site_id" in privilige and privilige['site_id'] == site_id:
                        if privilige["role"] in ["write", "admin"]:
                            return True
                console.error("authorization error")
                return False
        else:
            return True

    def _response(self, resp, uri=""):
        if resp.status_code == 200:
            result = resp.json()
            error = ""
            console.debug("Response Status Code: %s" % resp.status_code)
        else:
            result = ""
            error = resp.json()
            console.info("Response Status Code: %s" % resp.status_code)
            console.debug("Response: %s" % error)
        return {"result": result, "status_code": resp.status_code, "error": error, "uri":uri}

    def mist_get(self, uri, org_id="", site_id="", query=""):
        """GET HTTP Request
        Params: uri, HTTP query
        Return: HTTP response"""
        if self._check_authorization("GET", org_id=org_id, site_id=site_id):
            try:
                url = self._url(uri)
                console.info("Request > GET %s" % url)
                resp = self.session.get(url)
                resp.raise_for_status()
            except HTTPError as http_err:
                console.error(f'HTTP error occurred: {http_err}')  # Python 3.6
            except Exception as err:
                console.error(f'Other error occurred: {err}')  # Python 3.6
            else: 
                return self._response(resp, uri)
        else:
            console.error("you're not authenticated yet...")

    def mist_post(self, uri, org_id="", site_id="", body={}):
        """POST HTTP Request
        Params: uri, HTTP body
        Return: HTTP response"""
        if self._check_authorization("POST", org_id=org_id, site_id=site_id):
            try: 
                url = self._url(uri)
                console.info("Request > POST %s" % url)
                resp = self.session.post(url, json=body)
                resp.raise_for_status()
            except HTTPError as http_err:
                console.error(f'HTTP error occurred: {http_err}')  # Python 3.6
            except Exception as err:
                console.error(f'Other error occurred: {err}')  # Python 3.6
            else: 
                return self._response(resp, uri)
        else:
            console.error("you're not authenticated yet...")

    def mist_put(self, uri, org_id="", site_id="", body={}):
        """PUT HTTP Request
        Params: uri, HTTP body
        Return: HTTP response"""
        if self._check_authorization("PUT", org_id=org_id, site_id=site_id):
            try:
                url = self._url(uri)
                console.info("Request > PUT %s" % url)
                console.debug("Request body: \r\n%s" % body)
                resp = self.session.put(url, data=body)
                resp.raise_for_status()
            except HTTPError as http_err:
                console.error(f'HTTP error occurred: {http_err}')  # Python 3.6
            except Exception as err:
                console.error(f'Other error occurred: {err}')  # Python 3.6
            else: 
                return self._response(resp, uri)

        else:
            console.error("you're not authenticated yet...")

    def mist_delete(self, uri, org_id="", site_id=""):
        """DELETE HTTP Request
        Params: uri
        Return: HTTP response"""
        if self._check_authorization("DELETE", org_id=org_id, site_id=site_id):
            try: 
                url = self._url(uri)
                console.info("Request > DELETE %s" % url)
                resp = self.session.delete(url)
                resp.raise_for_status()
            except HTTPError as http_err:
                console.error(f'HTTP error occurred: {http_err}')  # Python 3.6
            except Exception as err:
                console.error(f'Other error occurred: {err}')  # Python 3.6
            else: 
                return self._response(resp, uri)
        else:
            console.error("you're not authenticated yet...")