'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import requests
import json
import weakref
from getpass import getpass

from .__req import Req
from .models.privilege import Privileges


try:
    from config import log_level
except:
    log_level = 6
finally:
    from .__debug import Console
    console = Console(log_level)
    

clouds = [
    {
        "short": "US", 
        "host": "api.mist.com"
    }, 
    {
        "short": "EU", 
        "host": "api.eu.mist.com"
    },    {
        "short": "GCP", 
        "host": "api.gc1.mist.com"
    }
]

#### PARAMETERS #####

class Mist_Session(Req):
    """Class managing REST login and requests"""

    def __init__(self, session_file=None, load_settings=True, email="", password="", apitoken=None, host=None):    

        # user and https session parameters
        self.host = host
        self.email = email
        self.password = password
        self.first_name = ""
        self.last_name = ""
        self.phone = ""
        self.via_sso = False
        self.privileges = Privileges([])
        self.session_expiry = ""
        self.tags = []
        self.authenticated = False
        self.session = requests.session()
        self.csrftoken = ""
        self.apitoken = apitoken
        #Try to log in
        if session_file != None:
            self._restore_session(session_file)
        if self.authenticated == False:
            self._credentials(load_settings)
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

    def _restore_session(self, file):                
        console.info("Restoring session...")
        try:
            with open(file, 'r') as f:
                for line in f:
                    line = line.replace('\n', '')
                    line = json.loads(line)
                    if "cookie" in line:
                        cookie = line["cookie"]
                        self.session.cookies.set(**cookie)
                    elif "host" in line:
                        self.host = line["host"]
            console.info("Session restored.")
            console.debug("Cookies > %s" % self.session.cookies)
            console.debug("Host > %s" % self.host) 
            self._set_authenticated(True)
            valid = self.getself()
            if valid == False:
                console.error("Session expired...")
                self._set_authenticated(False)

        except:
            console.error("Unable to load session...")      

    def _select_cloud(self):
        loop = True
        resp = "x"
        while loop:
            i=0
            print("\r\nAvailable Clouds:")
            for cloud in clouds:
                print("%s) %s (host: %s)" % (i, cloud["short"], cloud["host"]))
                i+=1
            resp = input("\r\nSelect a Cloud (0 to %s, or q to exit): " %i)
            if resp == "q":
                exit(0)    
            if resp == "i":
                return "api.mistsys.com"
            else:
                try:
                    resp_num = int(resp)
                    if resp_num >= 0 and resp_num <= i:
                        return clouds[resp_num]["host"]                        
                        loop = False
                    else:
                        print("Please enter a number between 0 and %s." %i)
                except:
                    print("Please enter a number.")

    def _credentials(self, load_settings=True):
        self.session = requests.session()
        try:
            if not load_settings:
                if not self.host: self._select_cloud()
                if not self.email: self.email = input("Login: ")
                if not self.password: self.password = getpass("Password: ")
            else:
                from config import credentials
                console.notice("Login file found.")
                if "host" in credentials: self.host = credentials["host"]
                else: self._select_cloud()
                if "apitoken" in credentials: self._set_apitoken(credentials["apitoken"])
                elif "email" in credentials: 
                    self.email = credentials["email"]
                    if "password" in credentials:
                            self.password = credentials["password"]
                    else: 
                        self.password = getpass("Password:")
                else:
                    console.error("Credentials invalid... Can't use the information from config.py...")
                    raise ValueError            
        except:
            console.notice("No login file found. Asking for credentials")
            if not self.host: self._select_cloud()
            self.email = input("Login: ")
            self.password = getpass("Password: ")
        finally:
            if self.host == "":
                self.host = self._select_cloud()
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
            if not self.apitoken: 
                self.csrftoken = self.session.cookies['csrftoken']
                self.session.headers.update({'X-CSRFToken': self.csrftoken})
        elif value == False:
            self.authenticated = False
            self.csrftoken = ""
            del self.session

    def get_authenticated(self):
        return self.authenticated or self.apitoken != None

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
            self._set_authenticated(True)
            return True
        else:
            console.error("2FA authentication failed")
            console.error("Error code: %s" % resp.status_code)
            exit(255)
            return False

    def two_factor_authentication_token(self, two_factor):        
        uri = "/api/v1/login/two_factor"
        body = { "two_factor": two_factor }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            console.notice("2FA authentication successed")
            self._set_authenticated(True)
            return True
        else:
            console.error("2FA authentication failed")
            console.error("Error code: %s" % resp.status_code)
            exit(255)
            return False        
    
    def getself(self):
        """Retrieve information about the current user and store them in the current object.
        Params: password (optional. Only needed for 2FA processing)
        Return: none"""
        uri = "/api/v1/self"
        resp = self.mist_get(uri)
        if resp != None and 'result' in resp:
            # Deal with 2FA if needed
            if (
                "two_factor_required" in resp['result']
                and resp['result']['two_factor_required'] == True
                and "two_factor_passed" in resp['result']
                and resp['result']['two_factor_passed'] == False
            ):
                two_factor = input("Two Factor Authentication code:")
                if (self.apitoken):
                    if (self.two_factor_authentication_token(two_factor) == True):
                        self.getself()
                elif (self.two_factor_authentication(two_factor) == True):
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
                return True
        else:
            console.error("Authentication not valid...")
            print()
            resp = input("Do you want to try with new credentials for %s (y/N)? " %(self.host))
            if resp.lower() == "y":
                self._credentials(load_settings=False)
                return self.getself()
            else:
                exit(0)

    def save(self, file_path="./session.py"):
        if self.apitoken != None:
            console.error("API Token used. There is no cookies to save...")
        else:
            console.warning("This will save in clear text your session cookies!")
            sure = input("Are you sure? (y/N)")
            if sure.lower() == "y":
                with open(file_path, 'w') as f:
                    for cookie in self.session.cookies:
                        cookie_json = json.dumps({"cookie":{"domain": cookie.domain, "name": cookie.name, "value": cookie.value}})
                        f.write("%s\r\n" % cookie_json)
                    host = json.dumps({"host": self.host})
                    f.write("%s\r\n" % host)
                console.info("session saved.")

def disp(data):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


