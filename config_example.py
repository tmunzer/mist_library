'''
~~~ OPTIONAL ~~~~

example of the "config.py" file where you can store the
account credenitals or API token. 
credentials variable may have two different format:
-------
1. Login/password

credentials = {
    "email": "user@domain",
    "password": "xxxxx",
    "host": 'api.mist.com'
}

OR

credentials = {
    "email": "user@domain",
    "host": 'api.mist.com'
}
-------
2. API Token

credentials = {
    "apitoken" : "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "host": "api.mist.com"
} 
-------
OTHER
Log level: you can define the log level displayed on the console with the following variable (default 
is 6):
log_level = 6

------ 
COMPLETE EXAMPLE

INFO: Be sure to uncomment the information to be used in your file!

The information in you config.py file should look like (of course, it depends on the authentication 
method you chose):

credentials = {
    "apitoken" : "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "host": "api.mist.com"
} 
log_level = 6
'''
