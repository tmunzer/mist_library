import requests
import json
import weakref
from getpass import getpass

from .req import Req
from .models.privilege import Privileges


try:
    from config import log_level
except:
    log_level = 6
finally:
    from .debug import Console
    console = Console(log_level)

#### PARAMETERS #####

class Mist_Session(Req):
    """Class managing REST login and requests"""

    def __init__(self):    

        # user and https session parameters
        self.host = ""
        self.email = ""
        self.password = ""
        self.first_name = ""
        self.last_name = ""
        self.phone = ""
        self.via_sso = False
        self.privileges = Privileges([])
        self.session_expiry = ""
        self.tags = []
        self.authenticated = False
        self.session = requests.session()
        self.session.headers.update({'Content-Type': "application/json"})
        self.csrftoken = ""
        self.apitoken = ""
        #Try to log in
        self._credentials()
        # if successfuly authenticated
        if (self.get_authenticated()): self.getself()
        # if authentication failed, exit with error code 255
        else:
            console.alert("Authentication failed... Exiting...") 
            exit(255)

    def __str__(self):
        fields = ["email", "first_name", "last_name", "phone", "via_sso",
                  "privileges", "session_expiry", "tags", "authenticated"]
        string = ""
        for field in fields:
            if hasattr(self, field) and getattr(self, field) != "":
                string += "%s:\r\n" % field
                if field == "privileges":
                    string += Privileges(self.privileges).display()
                    string += "\r\n"
                elif field == "tags":
                    for tag in self.tags:
                        string += "  -  %s\r\n" % tag
                elif field == "authenticated":
                    string += "%s\r\n" % self.get_authenticated()
                else:
                    string += "%s\r\n" % (getattr(self, field))
                string += "\r\n"
        return string

    def _credentials(self):
        try:
            from config import credentials
            console.notice("Login file found.")
            if "host" in credentials: self.host = credentials["host"]
            if "apitoken" in credentials: self._set_apitoken(credentials["apitoken"])
            elif "email" in credentials: 
                self.email = credentials["email"]
                if "password" in credentials:
                        self.password = credentials["password"]
                else: 
                    self.password = getpass("Password:")
            else:
                console.error("Credentials invalid... Can't use the information into secret.py...")
                raise ValueError            
        except:
            console.notice("No login file found. Asking for credentials")
            self.email = input("Login:")
            self.password = getpass("Password:")
        finally:
            if self.host == "":
                self.host = "api.mist.com"
            if self.email != "" and self.password != "":
                self._set_login_password()


    def _set_apitoken(self, apitoken):
        console.notice("API Token authentication used")
        self.apitoken = apitoken
        self.session.headers.update({'Authorization': "Token " + apitoken})

    def _set_login_password(self):
        """Function to authenticate a user. Will create and store a session used by other requests
        Params: email, password
        return: nothing"""
        console.debug("Credentials authentication used")
        uri = "/api/v1/login"
        body = {
            "email": self.email,
            "password": self.password
        }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            console.notice("authenticated")

            self._set_authenticated(True)
        elif resp.status_code == 400:
            console.error("not authenticated: " + resp.json["detail"])
        else:
            try:
                console.error(resp.json()["detail"])
            except:
                console.error(resp.text)

    def logout(self):
        uri = "/api/v1/logout"
        resp = self.mist_post(uri)
        if resp['status_code'] == 200:
            console.warning("Logged out")
            self._set_authenticated(False)
        else:
            try:
                console.error(resp.json()["detail"])
            except:
                console.error(resp.text)

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

    def list_api_token(self):
        uri = "https://%s/api/v1/self/apitokens" % self.host
        resp = self.session.get(uri)
        return resp

    def create_api_token(self):
        uri = "https://%s/api/v1/self/apitokens" % self.host
        resp = self.session.post(uri)
        return resp

    def delete_api_token(self, token_id):
        uri = "https://%s/api/v1/self/apitokens/%s" % (self.host, token_id)
        resp = self.session.delete(uri)
        return resp

    def two_factor_authentication(self, two_factor):
        uri = "/api/v1/login"
        body = {
            "email": self.email,
            "password": self.password,
            "two_factor": two_factor
        }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            console.notice("2FA authentication successed")
            return True
        else:
            console.error("2FA authentication failed")
            console.error("Error code: %s" % resp.status_code)
            return False

    def getself(self):
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
                if (self.two_factor_authentication(two_factor) == True):
                    self.getself()
            # Get details of the account 
            else:
                for key, val in resp['result'].items():
                    if key == "privileges":
                        self.privileges = Privileges(resp['result']["privileges"])
                    if key == "tags":
                        for tag in resp['result']["tags"]:
                            self.tags.append(tag)
                    else:
                        setattr(self, key, val)

def disp(data):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


