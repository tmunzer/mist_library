import requests
import json
import weakref

from req import Req
import lib_org
import lib_site

from tabulate import tabulate


class Privilege:
    def __init__(self, privilege):
        self.scope = ""
        self.org_id = ""
        self.org_name = ""
        self.msp_id = ""
        self.msp_name = ""
        self.orggroup_ids = ""
        self.name = ""
        self.role = ""
        self.site_id = ""
        self.sitegroup_ids = ""
        for key, val in privilege.items():
            setattr(self, key, val)

    def __str__(self):
        self.display()

    def display(self):
        fields = ["scope", "org_id", "org_name", "msp_id", "msp_name",
                  "orggroup_ids", "name", "role", "site_id", "sitegroup_ids"]
        string = ""
        for field in fields:
            if getattr(self, field) != "":
                string += "%s: %s \r\n" % (field, getattr(self, field))
        return string


class Mist(Req):
    """Class managing REST login and requests"""

    def __init__(self, host, email="", password="", apitoken=""):
        self.host = host
        self.email = email
        self.first_name = ""
        self.last_name = ""
        self.phone = ""
        self.via_sso = False
        self.privileges = []
        self.session_expiry = ""
        self.tags = []
        self.authenticated = False
        self.session = requests.session()
        self.csrftoken = ""
        self.apitoken = ""
        if (apitoken != ""):
            print("API Token authentication used")
            self.apitoken = apitoken
            self.session.headers.update({'Authorization': "Token " + apitoken})
        elif (email != "" and password != ""):
            print("Credentials authentication used")
            self.login(email, password)
        else:
            print("Missing credentials or API Token to log in")
            exit(255)
        if (self.get_authenticated()):
            self.getself(password)
            self.site = lib_site
            self.org = lib_org

    def __str__(self):
        fields = ["email", "first_name", "last_name", "phone", "via_sso",
                  "privileges", "session_expiry", "tags", "authenticated"]
        string = ""
        for field in fields:
            if field == "privileges":
                string += "privileges: " + "\r\n"
                i = 0
                for privilege in self.privileges:
                    i += 1
                    string += "  - #%s\r\n" % i
                    for field, value in privilege.items():
                        string += "    - %s: %s \r\n" % (field, value)
            elif field == "tags":
                string += "tags: " + "\r\n"
                for tag in self.tags:
                    string += "  - " + tag + "\r\n"
            elif getattr(self, field) != "":
                string += "%s: %s \r\n" % (field, getattr(self, field))
        return string

    def _set_authenticated(self, value):
        if value == True:
            self.authenticated = True
            self.csrftoken = self.session.cookies['csrftoken']
            self.session.headers.update({'X-CSRFToken': self.csrftoken})

        elif value == False:
            self.authenticated = False
            self.csrftoken = ""
            del self.session

    def get_authenticated(self):
        return self.authenticated or self.apitoken != ""

    def login(self, email, password):
        """Function to authenticate a user. Will create and store a session used by other requests
        Params: email, password
        return: nothing"""
        uri = "/api/v1/login"
        body = {
            "email": email,
            "password": password
        }
        resp = self.session.post(self._url(uri), json=body)
        print(resp)
        if resp.status_code == 200:
            print("authenticated")

            self._set_authenticated(True)
        elif resp.status_code == 400:
            print("not authenticated: " + resp.json["detail"])
        else:
            try:
                print(resp.json()["detail"])
            except:
                print(resp.text)

    def logout(self):
        uri = "/api/v1/logout"
        resp = self.mist_post(uri)
        if resp['status_code'] == 200:
            print("Logged out")
            self._set_authenticated(False)
        else:
            try:
                print(resp.json()["detail"])
            except:
                print(resp.text)

    def get_api_token(self):
        uri = "/api/v1/self/apitokens"
        resp = self.mist_post(uri)
        return resp

    def two_factor_authentication(self, two_factor, password):
        uri = "/api/v1/login"
        body = {
            "email": self.email,
            "password": password,
            "two_factor": two_factor
        }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            print("2FA authentication with success")
            return True
        else:
            print("2FA authentication failed")
            print("Error code: %s" % resp.status_code)
            return False

    def getself(self, password=""):
        """Retrieve information about the current user and store them in the current object.
        Params: password (optional. Only needed for 2FA processing)
        Return: none"""
        uri = "/api/v1/self"
        resp = self.mist_get(uri)
        if resp['result'] != "":
            # Deal with 2FA if needed
            if (
                "two_factor_required" in resp['result']
                and "two_factor_passed" in resp['result']
                and resp['result']['two_factor_required'] == True
                and resp['result']['two_factor_passed'] == False
            ):
                two_factor = input("Two Factor Authentication code:")
                if (self.two_factor_authentication(two_factor, password) == True):
                    self.getself()
            # Get details of the account 
            else:
                for key, val in resp['result'].items():
                    if key == "privileges":
                        for privilege in resp['result']["privileges"]:
                            priv = Privilege(privilege)
                        self.privileges.append(priv)
                    if key == "tags":
                        for tag in resp['result']["tags"]:
                            self.tags.append(tag)
                    else:
                        setattr(self, key, val)

    def display_dict(self, mdict):
        columns_headers = ["scope", "name", "site_id", "org_name", "org_id", 'msp_name', "msp_id" ]
        table = []
        for entry in mdict:
            temp = []
            for field in columns_headers:
                if field in entry:
                    temp.append(str(entry[field]))
                else:
                    temp.append("")
            table.append(temp)
        print("")
        print("--------------------------------")
        print("Privileges:")
        print(tabulate(table, columns_headers))

def disp(data):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


