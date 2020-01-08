
import json

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)


types_list = ["http-post", "splunk", "google-pubsub", "aws-sns"]
topics_list = [ "location", "zone", "vbeacon", "rssizone", "asset-raw", "device-events", "alarms", "audits", "client-sessions", "device-updowns" ]

class Webhook:

    def __init__(self, name = "", wh_type="http-post", url="", secret="", splunk_token="", verify_cert=False, enabled=True, topics=[]):
        self.name = name
        self.type = wh_type
        self.url = url
        self.secret = secret
        self.splunk_token = splunk_token
        self.verify_cert = verify_cert
        self.enabled = enabled
        self.topics = topics

    def __str__(self):
        string = ""
        string += "Name: %s\r\n" %self.name
        string += "Enabled: %s\r\n" %self.enabled
        string += "Type: %s\r\n" %self.type
        string += "URL: %s\r\n" %self.url
        string += "Secret: %s\r\n" %self.secret
        string += "Splunk Token: %s\r\n" %self.splunk_token
        string += "verify_cert: %s\r\n" %self.verify_cert
        string += "Topics: %s\r\n" %self.topics
        return string
        
    def toJSON(self):
        return json.dumps(self.__dict__)

    def define(self, name = "", wh_type="http-post", url="", secret="", splunk_token="", verify_cert=False, enabled=True, topics=[]):
        self.set_name(name)
        self.set_type(wh_type)
        self.set_url(url)
        self.set_secret(secret)
        self.set_splunk_token(splunk_token)
        self.set_verify_cert(verify_cert)
        self.set_enabled(enabled)
        self.set_topics(topics)

    def cli(self):
        resp = False
        while not resp:
            val = input("Name of the Webhook configuration: ")
            resp = self.set_name(val)
        resp = False
        while not resp:
            val = input("Enable the Webhook (Y/n)? ")
            if val.lower() == "n":
                val = False
                resp = self.set_enabled(val)
            elif val.lower() == "y" or val == "":
                val = True     
                resp = self.set_enabled(val)       
        if self.enabled == False:
            console.info("Webhook will be disabled.")
        resp = False
        while not resp:
            val = input("Enable the Server Certificate Validation (Y/n): ")
            if val.lower() == "n":
                val = False
                resp = self.set_verify_cert(val)
            elif val.lower() == "y" or val == "":
                val = True            
                resp = self.set_verify_cert(val)
        resp = False
        while not resp:
            val = input("URL of the Webhook receiver: ")
            resp = self.set_url(val)
        resp = False
        while not resp:
            print("Type of webhook:")                
            for i in  range(len(types_list)):
                print("%s) %s" % (i, types_list[i]))
            val = input("Please enter the number corresponding to your webhook type: ")                
            try:
                val_num = int(val)
                if val_num >= 0 and val_num < len(types_list):
                    resp = self.set_type(types_list[val_num])
            except:
                print("Please enter a number between 0 and %s" % len(types_list))
        resp = False
        if self.type == "http-post":
            while not resp:
                val = input("Please enter the HTTP-POST secret (if any): ")
                resp = self.set_secret(val)
        elif self.type == "splunk":
            while not resp:
                val = input("Please enter the Splunk Token (if any): ")
                resp = self.set_splunk_token(val)
        resp = False
        while not resp:
            for i in range(len(topics_list)):       
                print("%s) %s" % (i, topics_list[i]))
            vals = input("\r\nSelect topics you want to enable (0 to %s, \"0,1\" for topics 0 and 1, a for all): " %i)
            val_list = []            
            if vals == "a":
                resp = self.set_topics(topics_list)
            else:
                try:
                    val_splitted = resp.split(",")
                    val_list = []
                    for num in val_splitted:
                        index = int(num)
                        if resp_num >= 0 and resp_num < len(topics_list):
                            val_list.append(topics_list[index])                        
                        else:
                            print("%s is not part of the possibilities." % resp_num)                                                
                    resp = self.set_topics(val_list)
                except:
                    print("Only numbers are allowed.")

    def set_name(self, value):
        if value != "":
            self.name = value
            return True
        else:
            console.error("You must enter a name.")
            return False

    def set_type(self, value):        
        if value in types_list:            
            self.type = value
            return True
        else:
            console.error("Value %s is not accepted. Must be \"http-post\", \"splunk\", \"google-pubsub\" or \"aws-sns\"." %value)
            return False
    
    def set_url(self, value):
        if str(value).lower().startswith("https://"):            
            self.url = value
            return True
        else:
            console.error("Value %s is not accepted. Please enter a valid URL." %value)
            return False

    def set_secret(self, value):
        if self.type == "http-post":
            self.secret = value                
        else:
            console.warning("This settings is only used with \"http-post\" webhook types.Please configure the webhook at \"http-post\" first.")
        return True

    def set_splunk_token(self, value):
        if self.type == "splunk":
            self.splunk_token = value   
        else:
            console.warning("This settings is only used with \"splunk\" webhook types.Please configure the webhook at \"splunk\" first.")        
        return True         

    def set_verify_cert(self, value):
        try:
            verify = bool(value)
            self.verify_cert = verify
            return True
        except:
            console.error("Value %s is not accepted. Must be \"true\", \"false\", \"0\" or \"1\"." %value)
            return False

    def set_enabled(self, value):
        try:
            enabled = bool(value)
            self.enabled = enabled
            return True
        except:
            console.error("Value %s is not accepted. Must be \"true\", \"false\", \"0\" or \"1\"." %value)
            return False
    
    def set_topics(self, values_list):
        val = []
        for value in values_list:
            if value in topics_list:
                val.append(value)
            else:
                console.error("%s is not accepted." %value)
        self.topics = val
        return True
        