'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

from xxlimited import foo
import requests
import json
import sys
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
        "host": "api.mist.com",
        "cookies_ext": ""
    }, 
    {
        "short": "EU", 
        "host": "api.eu.mist.com",
        "cookies_ext": ".eu"
    },    
    {
        "short": "GCP", 
        "host": "api.gc1.mist.com",
        "cookies_ext": ".gc1"
    }
]

def header():
    print("".center(80, '-'))
    print(" Mist Python CLI Session ".center(80, "-"))
    print("")
    print(" Written by: Thomas Munzer (tmunzer@juniper.net)")
    print(" Github    : https://github.com/tmunzer/mist_library")
    print("")
    print(" This file is licensed under the MIT License.")
    print("")
    print("".center(80, '-'))
    print()
def footer():
    print()
    print("".center(80, '-'))
    print(" Mist Python CLI Session Initialized ".center(80, "-"))
    print("".center(80, '-'))
    print()


#### PARAMETERS #####

class Mist_Session(Req):
    """Class managing REST login and requests"""

    def __init__(self, session_file=None, load_settings=True, email="", password="", apitoken=None, host=None):    
        header()
        # user and https session parameters
        self.host = host
        self.email = email
        self.password = password
        self.first_name = ""
        self.last_name = ""
        self.via_sso = False
        self.privileges = Privileges([])
        self.session_expiry = ""
        self.tags = []
        self.authenticated = False
        self.session = requests.session()
        self.csrftoken = ""
        self.apitoken = apitoken

        #Try to log in
        if session_file is not None:
            self._restore_session(session_file)
        if load_settings:
            self._load_settings()
        
        if not self.host: self.host = self._select_cloud()

        # deepcode ignore PythonSameEvalBinaryExpressiontrue: self.authenticated is updated by self._restore_session()
        if not self.authenticated:
            self._login()
        # if successfuly authenticated
        if self.get_authenticated(): self.getself()
        # if authentication failed, exit with error code 255
        else:
            sys.exit(255)
        footer()


    def __str__(self):
        fields = ["email", "first_name", "last_name", "phone", "via_sso",
                  "privileges", "session_expiry", "tags", "authenticated"]
        string = ""
        for field in fields:
            if hasattr(self, field) and getattr(self, field) != "":
                string += f"{field}:\r\n"
                if field == "privileges":
                    string += Privileges(self.privileges).display()
                    string += "\r\n"
                elif field == "tags":
                    for tag in self.tags:
                        string += f"  -  {tag}\r\n"
                elif field == "authenticated":
                    string += f"{self.get_authenticated()}\r\n"
                else:
                    string += f"{getattr(self, field)}\r\n"
                string += "\r\n"
        return string


    def _restore_session(self, file):                
        console.debug("in  > _restore_session")
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
            console.debug(f"Cookies > {self.session.cookies}")
            console.debug(f"Host > {self.host}") 
            self._set_authenticated(True)
            valid = self.getself()
            if valid == False:
                console.info("Session expired...")
                self._set_authenticated(False)

        except:
            console.debug("Unable to load session...")      


    def _select_cloud(self):  
        console.debug("in  > _select_cloud")
        resp = "x"
        i=0
        print()
        print(" Mist Cloud Selection ".center(80, "-"))
        print()
        for cloud in clouds:
            print(f"{i}) {cloud['short']} (host: {cloud['host']})")
            i+=1

        print()
        resp = input(f"Select a Cloud (0 to {i}, or q to exit): ")
        if resp == "q":
            sys.exit(0)    
        elif resp == "i":
            return "api.mistsys.com"
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= i:
                    return clouds[resp_num]["host"]                        
                else:
                    print(f"Please enter a number between 0 and {i}.")
                    return self._select_cloud()
            except:
                print("\r\nPlease enter a number.")
                return self._select_cloud()

    def _load_settings(self):  
        console.debug("in  > _load_settings")
        self.session = requests.session()
        try:
            from config import credentials
            console.info("Config file loaded")
            self.host = credentials.get("host")

            if "apitoken" in credentials: 
                self.apitoken = credentials["apitoken"]
                self.session.headers.update({'Authorization': "Token " + self.apitoken})
                self._set_authenticated(True)
                console.info("Using API Token from config file")
            elif "email" in credentials: 
                self.email = credentials["email"]
                console.info(f"Using username {self.email} from config file")
                self.password = credentials.get("password")
                if not self.password:
                    self.password = getpass("Password:")
        except:
            console.info("No login file found")           

    def _login(self): 
        console.debug("in  > _login")
        """Function to authenticate a user. Will create and store a session used by other requests
        Params: email, password
        return: nothing"""
        print()
        print(" Login/Pwd authentication ".center(80, "-"))
        print()

        self.session = requests.session()
        if not self.email: self.email = input("Login: ")
        if not self.password: self.password = getpass("Password: ")

        uri = "/api/v1/login"
        body = {
            "email": self.email,
            "password": self.password
        }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            print()
            console.info("Authentication successful!")
            print()
            self._set_authenticated(True)
        else:
            print()
            console.error(f"Authentication failed: {resp.json().get('detail')}")
            self.email = None
            self.password = None
            print()
            self._set_login_password()

    def logout(self):  
        console.debug("in  > logout")
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
        console.debug("in  > _set_authenticated")
        if value == True:
            self.authenticated = True
            if not self.apitoken:
                try: 
                    cookies_ext = next(item["cookies_ext"] for item in clouds if item["host"] == self.host)
                except:
                    cookies_ext = ""
                self.csrftoken = self.session.cookies['csrftoken' + cookies_ext]
                self.session.headers.update({'X-CSRFToken': self.csrftoken})
        elif value == False:
            self.authenticated = False
            self.csrftoken = ""
            del self.session

    def get_authenticated(self):  
        console.debug("in  > get_authenticated")
        return self.authenticated or self.apitoken 

    def list_api_token(self):  
        console.debug("in  > list_api_token")
        uri = f"https://{self.host}/api/v1/self/apitokens"
        resp = self.session.get(uri)
        return resp

    def create_api_token(self):  
        console.debug("in  > create_api_token")
        uri = f"https://{self.host}/api/v1/self/apitokens"
        resp = self.session.post(uri)
        return resp

    def delete_api_token(self, token_id):  
        console.debug("in  > delete_api_token")
        uri = f"https://{self.host}/api/v1/self/apitokens/{token_id}"
        resp = self.session.delete(uri)
        return resp

    def two_factor_authentication(self, two_factor):  
        console.debug("in  > two_factor_authentication")
        uri = "/api/v1/login"
        body = {
            "email": self.email,
            "password": self.password,
            "two_factor": two_factor
        }
        resp = self.session.post(self._url(uri), json=body)
        if resp.status_code == 200:
            print()
            console.info("2FA authentication successed")
            self._set_authenticated(True)
            return True
        else:
            print()
            console.error("2FA authentication failed")
            console.error(f"Error code: {resp.status_code}")
            return False   
    
    def getself(self):  
        """Retrieve information about the current user and store them in the current object.
        Params: password (optional. Only needed for 2FA processing)
        Return: none"""
        console.debug("in  > getself")
        uri = "/api/v1/self"
        resp = self.mist_get(uri)
        if resp and "result" in resp:
            # Deal with 2FA if needed
            if (
                resp['result'].get('two_factor_required') is True
                and resp['result'].get('two_factor_passed') is False
            ):
                print()
                two_factor_ok = False
                while not two_factor_ok:
                    two_factor = input("Two Factor Authentication code required: ")                    
                    two_factor_ok = self.two_factor_authentication(two_factor)
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
                print()
                print(" Authenticated ".center(80, "-"))
                print()
                print(f"Welcome {self.first_name} {self.last_name}!")
                print()
                return True
        else:
            console.error("Authentication not valid...")
            print()
            resp = input(f"Do you want to try with new credentials for {self.host} (y/N)? " %())
            if resp.lower() == "y":
                self._set_login_password()
                return self.getself()
            else:
                sys.exit(0)

    def save(self, file_path="./session.py"):  
        console.debug("in  > save")
        if self.apitoken is not None:
            console.warning("API Token used. There is no cookies to save...")
        else:
            console.warning("This will save your session cookies in clear text !")
            sure = input("Are you sure? (y/N)")
            if sure.lower() == "y":
                with open(file_path, 'w') as f:
                    for cookie in self.session.cookies:
                        cookie_json = json.dumps({"cookie":{"domain": cookie.domain, "name": cookie.name, "value": cookie.value}})
                        f.write(f"{cookie_json}\r\n")
                    host = json.dumps({"host": self.host})
                    f.write(f"{host}\r\n")
                console.info("session saved.")

def disp(data):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))


