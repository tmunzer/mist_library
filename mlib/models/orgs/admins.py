
import json

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)


class Invite:

    def __init__(self):
        self.email = ""
        self.first_name = ""
        self.last_name = ""
        self.hours = 24
        self.privileges = []        

    def __str__(self):
        string = ""
        string += "Email: %s\r\n" %self.email
        string += "First Name: %s\r\n" %self.first_name
        string += "Last Name: %s\r\n" %self.last_name
        string += "Hours: %s\r\n" %self.hours
        string += "Privileges: %s\r\n" %self.privileges
        return string
        
    def toJSON(self):
        invite = {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "hours": self.hours,
            "privileges": self.privileges
        }
        return invite

    def define(self, email = "", first_name="", last_name="", hours=24, privileges=[]):
        self.set_email(email)
        self.set_first_name(first_name)
        self.set_last_name(last_name)
        self.set_hours(hours)
        self.set_privileges(privileges)
        
    # TODO
    def cli(self):
        resp = False
        while not resp:
            val = input("PSK Name: ")
            resp = self.set_name(val)
        resp = False
        while not resp:
            val = input("PSK Passphrase (8 to 63 characters): ")    
            resp = self.set_passphrase(val)
        resp = False
        while not resp:
            # TODO: retrieve the SSID list
            val = input("SSID Name: ")
            resp = self.set_ssid(val)
        resp = False
        while not resp:
            print("Type of usage:")
            for i in  range(len(usages_list)):
                print("%s) %s PSK" % (i, usages_list[i]))            
            val = input("Choose the type of PSK usage (default: 0): ")
            if val == "":
                resp = self.set_usage("multi")
            else:
                try:
                    val_num = int(val)
                    if val > 0 and val < len(usages_list):
                        resp = self.set_usage(val_num)
                    else:
                        print("Please enter a number between 0 and %s" % len(usages_list))
                except:
                    print("Please enter a number between 0 and %s" % len(usages_list))        
        resp = False
        while not resp:           
            val = input("VLAN ID (let empty if none): ")                
            resp = self.set_vlan_id(val)
        resp = False
        while not resp:
            val = input("MAC Address (if MAC Address binding only): ")
            resp = self.set_mac(val)



    def set_name(self, value):
        if value != "":
            self.name = value
            return True
        else:
            console.error("You must enter a name.")
            return False

    def set_passphrase(self, value):        
        if len(value) >= 8 and len(value)<=63:            
            self.passphrase = value
            return True
        elif len(value) == 64:         
            self.passphrase = value
            return True
        else:
            console.error("Passphrase must be 8 to 63 characters long, or 64 HEX.")
            return False
    
    def set_ssid(self, value):
        if value != "":          
            self.ssid = value
            return True
        else:
            console.error("Value %s is not accepted. Please enter a valid SSID name." %value)
            return False

    def set_usage(self, value):
        if value in usages_list:
            self.usage = value    
            return True  
        else:
            console.warning("Value %s is not accepted. Only \"multi\" and \"single\" are valid choices." % value)
        return True

    def set_vlan_id(self, value):
        if value == "" or value == 0:
            self.vlan_id = 0     
            return True
        else:
            try:
                vid = int(value)
                if vid > 0 and vid < 4095:
                    self.vlan_id = vid
                    return True
                else:
                    console.error("Value %s is not accepted. Please enter a valid VLAN Id (1 to 4094)." % value)
                    return False
            except:
                console.error("Value %s is not accepted. Please enter a valid VLAN Id (1 to 4094)." % value)
                return False  

    def set_mac(self, value):
        if value == "":
            self.mac = ""
            return True
        else:
            try:
                value = str(value)
                value = value.replace(":", "").replace("-", "")
                if re.match('^[0-9A-F]*$', value):
                    self.mac = value
                    return True
                else:
                    console.error("%s is not a valid MAC Address format." % value)
            except:
                console.error("%s is not a valid MAC Address format." % value)
                return False
