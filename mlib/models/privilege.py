
from tabulate import tabulate

class Privileges:
    def __init__(self, privileges):
        self.privileges = []
        for privilege in privileges:
            self.privileges.append(_Privilege(privilege))           

    def __str__(self):
        columns_headers = ["scope", "name", "site_id", "org_name", "org_id", 'msp_name', "msp_id" ]
        table = []
        for entry in self.privileges:
            temp = []
            for field in columns_headers:
                if hasattr(entry, field):
                    temp.append(str(getattr(entry, field)))
                else:
                    temp.append("")
            table.append(temp)
        return tabulate(table, columns_headers)

    def display(self):
        return str(self)
        

class _Privilege:
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
        fields = ["scope", "org_id", "org_name", "msp_id", "msp_name",
                  "orggroup_ids", "name", "role", "site_id", "sitegroup_ids"]
        string = ""
        for field in fields:
            if getattr(self, field) != "":
                string += "%s: %s \r\n" % (field, getattr(self, field))
        return string
