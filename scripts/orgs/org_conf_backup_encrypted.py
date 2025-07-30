"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization in AES encrypted file.
You can use the script "org_conf_deploy.py" to restore the generated backup 
files to an existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

The backup is AES encrypted with a randomly generated key. The encryption key
is stored in a RSA encrypted file (encrypted with a RSA public key). The RSA
Private key is required to be able to decrypt AES encryption key. 

The encrypted backup can be decrypted with the following script:
https://github.com/tmunzer/mist_library/blob/master/scripts/utils/encryption.py

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/
pycryptodome: https://pypi.org/project/pycryptodome/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-p, --puk=              path to the RSA public key

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -p ./rsa.pub

"""


#### IMPORTS ####
import logging
import json
import datetime
import urllib.request
import os
import signal
import sys
import getopt
import getpass
from base64 import b64encode
from hashlib import sha256
try:
    from Cryptodome.Cipher import AES, PKCS1_OAEP
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Random import get_random_bytes
except:
    print(
        """
        Critical: 
        \"pycryptodome\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install pycryptodomex

        # Windows
        py -m pip install pycryptodomex
        """
    )
    sys.exit(3)

MISTAPI_MIN_VERSION = "0.52.0"

try:
    import mistapi
    from mistapi.__logger import console
except:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)

#####################################################################
#### PARAMETERS #####
DEFAULT_BACKUP_FOLDER = "./org_backup"
BACKUP_FILE = "org_conf_file.json"
LOG_FILE = "./script.log"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
SYS_EXIT = False

def sigint_handler(signal, frame):
    global SYS_EXIT
    SYS_EXIT = True
    ("[Ctrl C],KeyboardInterrupt exception occured.")

signal.signal(signal.SIGINT, sigint_handler)
#####################################################################
# BACKUP OBJECTS REFS
ORG_STEPS = {
    "data": {
        "mistapi_function": mistapi.api.v1.orgs.orgs.getOrg,
        "text": "Org info",
        "check_next": False,
    },
    "settings": {
        "mistapi_function": mistapi.api.v1.orgs.setting.getOrgSettings,
        "text": "Org settings",
        "check_next": False,
    },
    "sites": {
        "mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites,
        "text": "Org Sites",
        "check_next": True,
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.orgs.webhooks.listOrgWebhooks,
        "text": "Org webhooks",
        "check_next": True,
    },
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters,
        "text": "Org assetfilters",
        "check_next": True,
    },
    "alarmtemplates": {
        "mistapi_function": mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        "text": "Org alarmtemplates",
        "check_next": True,
    },
    "deviceprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Org deviceprofiles",
        "check_next": True,
    },
    "switchprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Org switchprofiles",
        "request_type": "switch",
        "check_next": True,
    },
    "hubprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Org hubprofiles",
        "request_type": "gateway",
        "check_next": True,
    },
    "mxclusters": {
        "mistapi_function": mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters,
        "text": "Org mxclusters",
        "check_next": True,
    },
    "mxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels,
        "text": "Org mxtunnels",
        "check_next": True,
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.orgs.psks.listOrgPsks,
        "text": "Org psks",
        "check_next": True,
    },
    "pskportals": {
        "mistapi_function": mistapi.api.v1.orgs.pskportals.listOrgPskPortals,
        "text": "Org pskportals",
        "check_next": True,
    },
    "rftemplates": {
        "mistapi_function": mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        "text": "Org rftemplates",
        "check_next": True,
    },
    "networktemplates": {
        "mistapi_function": mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        "text": "Org networktemplates",
        "check_next": True,
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        "text": "Org evpn_topologies",
        "check_next": True,
    },
    "services": {
        "mistapi_function": mistapi.api.v1.orgs.services.listOrgServices,
        "text": "Org services",
        "check_next": True,
    },
    "networks": {
        "mistapi_function": mistapi.api.v1.orgs.networks.listOrgNetworks,
        "text": "Org networks",
        "check_next": True,
    },
    "gatewaytemplates": {
        "mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates,
        "text": "Org gatewaytemplates",
        "check_next": True,
    },
    "vpns": {
        "mistapi_function": mistapi.api.v1.orgs.vpns.listOrgsVpns,
        "text": "Org vpns",
        "check_next": True,
    },
    "secpolicies": {
        "mistapi_function": mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        "text": "Org secpolicies",
        "check_next": True,
    },
    "servicepolicies": {
        "mistapi_function": mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies,
        "text": "Org servicepolicies",
        "check_next": True,
    },
    "sitegroups": {
        "mistapi_function": mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups,
        "text": "Org sitegroups",
        "check_next": True,
    },
    "sitetemplates": {
        "mistapi_function": mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates,
        "text": "Org sitetemplates",
        "check_next": True,
    },
    "ssos": {
        "mistapi_function": mistapi.api.v1.orgs.ssos.listOrgSsos,
        "text": "Org ssos",
        "check_next": True,
    },
    "ssoroles": {
        "mistapi_function": mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles,
        "text": "Org ssoroles",
        "check_next": True,
    },
    "templates": {
        "mistapi_function": mistapi.api.v1.orgs.templates.listOrgTemplates,
        "text": "Org templates",
        "check_next": True,
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.orgs.wxrules.listOrgWxRules,
        "text": "Org wxrules",
        "check_next": True,
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.orgs.wxtags.listOrgWxTags,
        "text": "Org wxtags",
        "check_next": True,
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels,
        "text": "Org wxtunnels",
        "check_next": True,
    },
    "nactags": {
        "mistapi_function": mistapi.api.v1.orgs.nactags.listOrgNacTags,
        "text": "Org nactags",
        "check_next": True,
    },
    "nacrules": {
        "mistapi_function": mistapi.api.v1.orgs.nacrules.listOrgNacRules,
        "text": "Org nacrules",
        "check_next": True,
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.orgs.wlans.listOrgWlans,
        "text": "Org wlans",
        "check_next": True,
    },
}
SITE_STEPS = {
    "assets": {
        "mistapi_function": mistapi.api.v1.sites.assets.listSiteAssets,
        "text": "Site assets",
        "check_next": True,
    },
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.sites.assetfilters.listSiteAssetFilters,
        "text": "Site assetfilters",
        "check_next": True,
    },
    "beacons": {
        "mistapi_function": mistapi.api.v1.sites.beacons.listSiteBeacons,
        "text": "Site beacons",
        "check_next": True,
    },
    "maps": {
        "mistapi_function": mistapi.api.v1.sites.maps.listSiteMaps,
        "text": "Site maps",
        "check_next": True,
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.sites.psks.listSitePsks,
        "text": "Site psks",
        "check_next": True,
    },
    "rssizones": {
        "mistapi_function": mistapi.api.v1.sites.rssizones.listSiteRssiZones,
        "text": "Site rssizones",
        "check_next": True,
    },
    "settings": {
        "mistapi_function": mistapi.api.v1.sites.setting.getSiteSetting,
        "text": "Site settings",
        "check_next": False,
    },
    "vbeacons": {
        "mistapi_function": mistapi.api.v1.sites.vbeacons.listSiteVBeacons,
        "text": "Site vbeacons",
        "check_next": True,
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.sites.webhooks.listSiteWebhooks,
        "text": "Site webhooks",
        "check_next": True,
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.sites.wlans.listSiteWlans,
        "text": "Site wlans",
        "check_next": True,
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.sites.wxrules.listSiteWxRules,
        "text": "Site wxrules",
        "check_next": True,
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.sites.wxtags.listSiteWxTags,
        "text": "Site wxtags",
        "check_next": True,
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.sites.wxtunnels.listSiteWxTunnels,
        "text": "Site wxtunnels",
        "check_next": True,
    },
    "zones": {
        "mistapi_function": mistapi.api.v1.sites.zones.listSiteZones,
        "text": "Site zones",
        "check_next": True,
    },
}

#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
#### ENCRYPTION/DECRYPTION
class EncryptionHandler:
    """
    class to manage Mist library encryption/decryption

    PARAMS
    -------
    backup_folder : str
        path to the folder where the data is/will be stored
    backup_file_name : str
        file name used to/to use to save the encrypted/decrypted data
        will be used to generate the following file names
        decrypted data file name: f"{backup_file_name}.json"
        encrypted data file name: f"{backup_file_name}.enc"
        encryption key file name: f"{backup_file_name}.key"
    """

    def __init__(self, backup_folder: str, backup_file_name: str) -> None:
        if backup_file_name.find(".") > 0:
            file_name = ".".join(backup_file_name.split(".")[:-1])
        else:
            file_name = backup_file_name
        self.backup_folder = self._check_path(backup_folder)
        self.decrypted_file_path = os.path.join(
            self.backup_folder, f"{file_name}.json"
        )
        self.encrypted_file_path = os.path.join(
            self.backup_folder, f"{file_name}.enc"
        )
        self.encryption_key_path = os.path.join(
            self.backup_folder, f"{file_name}.key"
        )

    def _check_path(self, path_to_check: str):
        if path_to_check.startswith("~/"):
            path_to_check = os.path.join(
                os.path.expanduser("~"), path_to_check.replace("~/", "")
            )
        return path_to_check

    def _derive_key_and_iv(self, aes_key, salt, key_length, iv_length):
        d = d_i = b""
        while len(d) < key_length + iv_length:
            # obtain the md5 hash value
            d_i = sha256(d_i + str.encode(aes_key) + salt).digest()
            d += d_i
        return d[:key_length], d[key_length : key_length + iv_length]

    ###########################################################################
    ####### AES KEY PROCESSING
    def _generate_aes_key(self, key_length):
        random_key = os.urandom(key_length)
        aes_key = b64encode(random_key).decode("utf-8")
        return aes_key

    def _save_aes_key(self, aes_key, rsa_puk_path: str):
        data = aes_key.encode("utf-8")
        puk_path = self._check_path(rsa_puk_path)
        puk = RSA.import_key(open(puk_path).read())
        session_key = get_random_bytes(16)
        cipher_rsa = PKCS1_OAEP.new(puk)
        enc_session_key = cipher_rsa.encrypt(session_key)
        cipher_aes = AES.new(session_key, AES.MODE_EAX)
        cipher_text, tag = cipher_aes.encrypt_and_digest(data)

        with open(self.encryption_key_path, "wb") as f:
            [f.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, cipher_text)]

    def _load_aes_key(self, rsa_prk_path: str):
        secret_code = getpass.getpass("Private Key Password (empty for none): ")
        prk_path = self._check_path(rsa_prk_path)
        prk = RSA.import_key(open(prk_path).read(), passphrase=secret_code)

        with open(self.encryption_key_path, "rb") as f:
            enc_session_key, nonce, tag, ciphertext = [
                f.read(x) for x in (prk.size_in_bytes(), 16, 16, -1)
            ]

        # Decrypt the session key with the private RSA key
        cipher_rsa = PKCS1_OAEP.new(prk)
        session_key = cipher_rsa.decrypt(enc_session_key)

        # Decrypt the data with the AES session key
        cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
        data = cipher_aes.decrypt_and_verify(ciphertext, tag)
        return data.decode("utf-8")

    ###########################################################################
    ####### IN MEMORY PROCESSING
    def encrypt_memory(
        self, decrypted_data: str, rsa_puk_path: str, key_length: int = 32
    ):
        """
        Function to generate encrypted file based on in memory data.
        The generated AES key is RSA encrypted with the public key and
        saved into a separete file

        PARAMS
        -------
        decrypted_data : str
            data to encrypt, as string
        rsa_puk_path : str
            path to the RSA Public key
        key_length : int, default 32
            aes key length to generate
        """
        aes_key = self._generate_aes_key(key_length)
        backup_bytes = decrypted_data.encode("utf-8")

        self._save_aes_key(aes_key, rsa_puk_path)

        with open(self.encrypted_file_path, "wb") as out_file:
            bs = AES.block_size  # 16 bytes
            salt = os.urandom(bs)  # return a string of random bytes
            key, iv = self._derive_key_and_iv(aes_key, salt, key_length, bs)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            out_file.write(salt)
            finished = False
            chunk_index = 0
            chunk_size = 1024 * bs
            while not finished:
                # chunk = in_file.read(1024 * bs)
                chunk = backup_bytes[chunk_index : chunk_index + chunk_size]
                chunk_index += chunk_size
                # final block/chunk is padded before encryption
                if len(chunk) == 0 or len(chunk) % bs != 0:
                    padding_length = (bs - len(chunk) % bs) or bs
                    chunk += str.encode(padding_length * chr(padding_length))
                    finished = True
                out_file.write(cipher.encrypt(chunk))

    def decrypt_memory(self, rsa_prk_path: str, key_length: int = 32):
        """
        Function to decrypt an encrypted file based on in memory data.
        This will use the RSA Private key to decrypt the AES key used
        to encrypt the file.

        PARAMS
        -------
        rsa_prk_path : str
            path to the RSA Private key
        key_length : int, default 32
            aes key length to generate
        """
        aes_key = self._load_aes_key(rsa_prk_path)

        with open(self.encrypted_file_path, "rb") as in_file:
            bs = AES.block_size
            salt = in_file.read(bs)
            key, iv = self._derive_key_and_iv(aes_key, salt, key_length, bs)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            next_chunk = ""
            data = ""
            finished = False
            while not finished:
                chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
                if len(next_chunk) == 0:
                    padding_length = chunk[-1]
                    chunk = chunk[:-padding_length]
                    finished = True
                if isinstance(chunk, bytes):
                    chunk_string = str(chunk, "utf-8")
                else:
                    chunk_string = chunk
                data += chunk_string

        decrypted_data = json.loads(data)
        with open(self.decrypted_file_path, "w") as out_file:
            json.dump(decrypted_data, out_file)

    ###########################################################################
    ####### FILE PROCESSING
    def encrypt_file(self, rsa_puk_path: str, key_length: int = 32):
        """
        Function to generate encrypted file based on a source file.
        The generated AES key is RSA encrypted with the public key and
        saved into a separete file

        PARAMS
        -------
        decrypted_file_path : str
            path to the source file
        rsa_puk_path : str
            path to the RSA Public key
        key_length : int, defauklt 32
            aes key length to generate
        """
        aes_key = self._generate_aes_key(key_length)
        self._save_aes_key(aes_key, rsa_puk_path)

        with open(self.decrypted_file_path, "rb") as in_file, open(
            self.encrypted_file_path, "wb"
        ) as out_file:
            bs = AES.block_size  # 16 bytes
            salt = os.urandom(bs)  # return a string of random bytes
            key, iv = self._derive_key_and_iv(aes_key, salt, key_length, bs)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            out_file.write(salt)
            finished = False
            while not finished:
                chunk = in_file.read(1024 * bs)
                # final block/chunk is padded before encryption
                if len(chunk) == 0 or len(chunk) % bs != 0:
                    padding_length = (bs - len(chunk) % bs) or bs
                    chunk += str.encode(padding_length * chr(padding_length))
                    finished = True
                out_file.write(cipher.encrypt(chunk))

    def decrypt_file(self, rsa_prk_path: str, key_length: int = 32):
        """
        Function to decrypt an encrypted file based on a source file.
        This will use the RSA Private key to decrypt the AES key used
        to encrypt the file.

        PARAMS
        -------
        rsa_prk_path : str
            path to the RSA Private key
        key_length : int, default 32
            aes key length to generate
        """
        aes_key = self._load_aes_key(rsa_prk_path)

        with open(self.encrypted_file_path, "rb") as in_file, open(
            self.decrypted_file_path, "wb"
        ) as out_file:
            bs = AES.block_size
            salt = in_file.read(bs)
            key, iv = self._derive_key_and_iv(aes_key, salt, key_length, bs)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            next_chunk = ""
            finished = False
            while not finished:
                chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
                if len(next_chunk) == 0:
                    padding_length = chunk[-1]
                    chunk = chunk[:-padding_length]
                    finished = True
                out_file.write(bytes(x for x in chunk))

#####################################################################
#### FUNCTIONS ####
def _backup_wlan_portal(org_id, site_id, wlans):
    for wlan in wlans:
        wlan_id = wlan["id"]
        if not site_id:
            portal_file_name = f"{FILE_PREFIX}_org_{org_id}_wlan_{wlan_id}.json"
            portal_image = f"{FILE_PREFIX}_org_{org_id}_wlan_{wlan_id}.png"
        else:
            portal_file_name = (
                f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.json"
            )
            portal_image = (
                f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.png"
            )
        if "portal_template_url" in wlan and wlan["portal_template_url"]:
            try:
                message = f"portal template for wlan {wlan_id}"
                PB.log_message(message)
                urllib.request.urlretrieve(
                    wlan["portal_template_url"], portal_file_name
                )
                PB.log_success(message)
            except Exception as e:
                PB.log_failure(message)
                LOGGER.error("Exception occurred", exc_info=True)
        if "portal_image" in wlan and wlan["portal_image"]:
            try:
                message = f"portal image for wlan {wlan_id}"
                PB.log_message(message)
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                PB.log_success(message)
            except Exception as e:
                PB.log_failure(message)
                LOGGER.error("Exception occurred", exc_info=True)

def _do_backup(
    mist_session,
    backup_function,
    check_next,
    scope_id,
    message,
    request_type: str = None,
):
    if SYS_EXIT:
        sys.exit(0)
    try:
        PB.log_message(message)
        if request_type:
            response = backup_function(mist_session, scope_id, type=request_type)
        else:
            response = backup_function(mist_session, scope_id)

        if check_next:
            data = mistapi.get_all(mist_session, response)
        else:
            data = response.data
        PB.log_success(message, True)
        return data
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
        return None

#### BACKUP ####
def _backup_full_org(mist_session, org_id, org_name):
    PB.log_title(f"Backing up Org {org_name}")
    backup = {}
    backup["org"] = {"id": org_id}

    ### ORG BACKUP
    for step_name, step in ORG_STEPS.items():
        request_type = step.get("request_type")
        backup["org"][step_name] = _do_backup(
            mist_session,
            step["mistapi_function"],
            step["check_next"],
            org_id,
            step["text"],
            request_type,
        )
    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])

    ### SITES BACKUP
    backup["sites"] = {}
    for site in backup["org"]["sites"]:
        site_id = site["id"]
        site_name = site["name"]
        site_backup = {}
        PB.log_title(f"Backing up Site {site_name}")
        for step_name, step in SITE_STEPS.items():
            site_backup[step_name] = _do_backup(
                mist_session,
                step["mistapi_function"],
                step["check_next"],
                site_id,
                step["text"],
            )
        backup["sites"][site_id] = site_backup

        if site_backup["wlans"]:
            _backup_wlan_portal(org_id, site_id, site_backup["wlans"])

        message = "Site map images"
        PB.log_message(message)
        try:
            for xmap in site_backup["maps"]:
                url = None
                if "url" in xmap:
                    url = xmap["url"]
                    xmap_id = xmap["id"]
                if url:
                    image_name = (
                        f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_map_{xmap_id}.png"
                    )
                    urllib.request.urlretrieve(url, image_name)
            PB.log_success(message)
        except Exception as e:
            PB.log_failure(message)
            LOGGER.error("Exception occurred", exc_info=True)

    PB.log_title("Backup Done", end=True)
    return backup

def _save_to_file(
        backup:dict,
        backup_folder:str,
        backup_name:str,
        puk_path:str
        ):
    backup_path = os.path.join(backup_folder, backup_name)
    try:
        if puk_path:
            message = f"Saving to encrypted backup to {backup_path} "
            PB.log_title(message, end=True, display_pbar=False)
            eh = EncryptionHandler("./", BACKUP_FILE)
            eh.encrypt_memory(json.dumps(backup), puk_path)
            PB.log_success(message, display_pbar=False)
        else:
            message = f"Saving to file {backup_path} "
            PB.log_title(message, end=True, display_pbar=False)
            with open(BACKUP_FILE, "w") as f:
                json.dump(backup, f)
            PB.log_success(message, display_pbar=False)
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)

def _start_org_backup(
        mist_session:mistapi.APISession,
        org_id:str,
        org_name:str,
        backup_folder:str,
        backup_name:str,
        puk_path:str
        ) -> bool:
    # FOLDER
    try:
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        os.chdir(backup_folder)
        if not os.path.exists(backup_name):
            os.makedirs(backup_name)
        os.chdir(backup_name)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    # PREPARE PROGRESS BAR
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id)
        sites = mistapi.get_all(mist_session, response)
        PB.set_steps_total(len(ORG_STEPS) + len(sites) * len(SITE_STEPS))
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    # BACKUP
    try:
        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup, backup_folder, backup_name, puk_path)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    return True

def start(
    mist_session: mistapi.APISession,
    org_id: str,
    backup_folder_param: str = None,
    backup_name:str=None,
    backup_name_date:bool=False,
    backup_name_ts:bool=False,
    puk_path:str=None
):
    """
    Start the process to deploy a backup/template

    PARAMS
    -------
    apisession : mistapi.APISession 
        mistapi session, already logged in
    org_id : str 
        only if the destination org already exists. org_id where to deploy the
        configuration
    backup_folder_param : str 
        Path to the folder where to save the org backup (a subfolder will be
        created with the org name). 
        default is "./org_backup"
    backup_name : str
        Name of the subfolder where the the backup files will be saved
        default is the org name
    backup_name_date : bool, default = False
        if `backup_name_date`==`True`, append the current date and time (ISO 
        format) to the backup name 
    backup_name_ts : bool, default = False
        if `backup_name_ts`==`True`, append the current timestamp to the backup 
        name 
    puk_path : str, Default None
        file path to save the RSA Private key. If None, the backup will not be encrypted

    RETURNS
    -------
    bool
        success status of the backup process. Returns False if the process
        didn't ended well
    """
    LOGGER.debug(f"org_conf_backup:start")
    LOGGER.debug(f"org_conf_backup:start:parameters:org_id:{org_id}")
    LOGGER.debug(f"org_conf_backup:start:parameters:backup_folder_param:{backup_folder_param}")
    LOGGER.debug(f"org_conf_backup:start:parameters:backup_name:{backup_name}")
    LOGGER.debug(f"org_conf_backup:start:parameters:backup_name_date:{backup_name_date}")
    LOGGER.debug(f"org_conf_backup:start:parameters:backup_name_ts:{backup_name_ts}")
    current_folder = os.getcwd()
    if not backup_folder_param:
        backup_folder_param = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    success = _start_org_backup(mist_session, org_id, org_name, backup_folder_param, backup_name, puk_path)
    os.chdir(current_folder)
    return success

#####################################################################
# USAGE
def usage(error_message:str=None):
    """display usage"""
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization in AES encrypted file.
You can use the script "org_conf_deploy.py" to restore the generated backup 
files to an existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

The backup is AES encrypted with a randomly generated key. The encryption key
is stored in a RSA encrypted file (encrypted with a RSA public key). The RSA
Private key is required to be able to decrypt AES encryption key. 

The encrypted backup can be decrypted with the following script:
https://github.com/tmunzer/mist_library/blob/master/scripts/utils/encryption.py

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/
pycryptodome: https://pypi.org/project/pycryptodome/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-p, --puk=              path to the RSA public key

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -p ./rsa.pub

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__
        )


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:e:l:b:dtp:",
            [
                "help",
                "org_id=",
                "env=",
                "log_file=",
                "backup_folder=",
                "datetime",
                "timestamp",
                "puk="
            ]
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    BACKUP_FOLDER = DEFAULT_BACKUP_FOLDER
    BACKUP_NAME = False
    BACKUP_NAME_DATE = False
    BACKUP_NAME_TS = False
    PUK_PATH = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-b", "--backup_folder"]:
            BACKUP_FOLDER = a
        elif o in ["-d", "--datetime"]:
            if BACKUP_NAME_TS:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                BACKUP_NAME_DATE = True
        elif o in ["-t", "--timestamp"]:
            if BACKUP_NAME_DATE:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                BACKUP_NAME_TS = True
        elif o in ["-p", "--puk"]:
            PUK_PATH = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    start(
        APISESSION,
        ORG_ID,
        BACKUP_FOLDER,
        BACKUP_NAME,
        BACKUP_NAME_DATE,
        BACKUP_NAME_TS,
        PUK_PATH
    )
