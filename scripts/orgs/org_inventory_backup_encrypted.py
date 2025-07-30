"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup all the devices from an organization in AES encrypted
file.
It will backup the devices claim codes (if any), configuration (including
position on the maps) and  pictures.
You can use the script "org_inventory_deploy.py" to restore the generated backup 
files to an existing organization or to a new one.

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
python3 ./org_inventory_backup.py     
python3 ./org_inventory_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -p ./rsa.pub

"""

#### IMPORTS ####
import logging
import sys
import os
import datetime
import json
import getopt
import urllib.request
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
        python3 -m pip install pycryptodome

        # Windows
        py -m pip install pycryptodome
        """
    )
    sys.exit(3)


MISTAPI_MIN_VERSION = "0.44.1"

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
BACKUP_FILE = "org_inventory_file.json"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
# BACKUP OBJECTS REFS
DEVICE_TYPES = ["ap", "switch", "gateway", "mxedge"]


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """

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
        print(backup_file_name)
        if backup_file_name.find(".") > 0:
            file_name = ".".join(backup_file_name.split(".")[:-1])
        else:
            file_name = backup_file_name
        print(file_name)
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
#### SITE FUNCTIONS ####
def _save_site_info(site: dict, backup: dict):
    backup["org"]["sites"][site["name"]] = {
        "id": site["id"],
        "old_maps_ids": {},
        "devices": [],
    }
    backup["org"]["old_sites_id"][site["name"]] = site["id"]


def _backup_site_id_dict(site: dict, backup: dict):
    if site["name"] in backup["org"]["sites"]:
        console.warning(f"Two sites are using the same name {site['name']}!")
        console.warning(
            "This will cause issue during the backup and the restore process."
        )
        console.warning("I recommand you to rename one of the two sites.")
        loop = True
        while loop:
            resp = input("Do you want to continue anyway (y/N)? ")
            if resp.lower() == "y":
                loop = False
                _save_site_info(site, backup)
            elif resp.lower() == "n" or resp == "":
                loop = False
                sys.exit(200)
    else:
        _save_site_info(site, backup)


def _backup_site_maps(mist_session: mistapi.APISession, site):
    response = mistapi.api.v1.sites.maps.listSiteMaps(mist_session, site["id"])
    backup_maps = mistapi.get_all(mist_session, response)
    maps_ids = {}
    for xmap in backup_maps:
        if xmap["name"] in maps_ids:
            console.warning(
                f"Two maps are using the same name {xmap['name']} in the same site {site['name']}!"
            )
            console.warning(
                "This will cause issue during the backup and the restore process."
            )
            console.warning("It is recommanded you to rename one of the two maps.")
            loop = True
            while loop:
                resp = input("Do you want to continue anyway (y/N)? ")
                if resp.lower() == "y":
                    loop = False
                    ["maps"].append({xmap["name"]: xmap["id"]})
                    ["maps_ids"][xmap["name"]] = xmap["id"]
                elif resp.lower() == "n" or resp == "":
                    loop = False
                    sys.exit(200)
        else:
            maps_ids[xmap["name"]] = xmap["id"]
    return maps_ids


def _no_magic(backup: dict, site_name: str, device: dict, device_type: str = None):
    if not device["mac"] in backup["org"]["magics"]:
        backup["org"]["devices_without_magic"].append(
            {
                "site": site_name,
                "device_type": device.get("type", device_type),
                "model": device.get("model"),
                "name": device.get("name"),
                "mac": device.get("mac"),
                "serial": device.get("serial"),
            }
        )


#####################################################################
#### INVENTORY FUNCTIONS ####
def _backup_inventory(
    mist_session: mistapi.APISession,
    org_id: str,
    org_name: str = None,
    backup: dict = {},
):
    PB.log_title(f"Backing up Org {org_name} Elements ")

    backup["org"]["id"] = org_id
    ################################################
    ##  Backing up inventory
    for device_type in DEVICE_TYPES:
        message = f"Backing up {device_type} magics"
        PB.log_message(message)
        try:
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                mist_session, org_id, type=device_type, limit=1000
            )
            inventory = mistapi.get_all(mist_session, response)
            for data in inventory:
                if data.get("magic"):
                    backup["org"]["magics"][data["mac"]] = data["magic"]
                    backup["org"]["devices"].append({
                        "mac": data["mac"],
                        "serial": data["serial"],
                        "type": data["type"],
                    })
            PB.log_success(message, True)
        except Exception as e:
            PB.log_failure(message, True)
            LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving org MxEdges

    message = f"Backing up Org MxEdges"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.mxedges.listOrgMxEdges(
            mist_session, org_id, limit=1000
        )
        mxedges = mistapi.get_all(mist_session, response)
        backup["org"]["mxedges"] = mxedges
        PB.log_success(message, True)
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
    for mxedge in mxedges:
        _no_magic(backup, "Org", mxedge, "mxedge")

    ################################################
    ##  Retrieving device profiles
    message = f"Backing up Device Profiles"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles(
            mist_session, org_id, limit=1000
        )
        deviceprofiles = mistapi.get_all(mist_session, response)
        for deviceprofile in deviceprofiles:
            backup["org"]["old_deviceprofiles_id"][
                deviceprofile["name"]
            ] = deviceprofile["id"]
        PB.log_success(message, True)
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
    ################################################
    ##  Retrieving evpntopologies
    message = f"Backing up EVPN Topologies"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies(
            mist_session, org_id
        )
        evpn_topologies = mistapi.get_all(mist_session, response)
        for evpn_topology in evpn_topologies:
            backup["org"]["old_evpntopo_id"][deviceprofile["name"]] = evpn_topology[
                "id"
            ]
        PB.log_success(message, True)
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving Sites list
    message = f"Retrieving Sites list"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
            mist_session, org_id, limit=1000
        )
        sites = mistapi.get_all(mist_session, response)
        PB.log_success(message, True)
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ## Backing up Sites Devices
    for site in sites:
        PB.log_title(f"Backing up Site {site['name']}")
        message = f"Devices List"
        PB.log_message(message)
        try:
            _backup_site_id_dict(site, backup)
            backup["org"]["sites"][site["name"]]["old_maps_ids"] = _backup_site_maps(
                mist_session, site
            )
            response = mistapi.api.v1.sites.devices.listSiteDevices(
                mist_session, site["id"], type="all", limit=1000
            )
            devices = mistapi.get_all(mist_session, response)
            backup["org"]["sites"][site["name"]]["devices"] = devices
            PB.log_success(message, True)
        except Exception as e:
            PB.log_failure(message, True)
            LOGGER.error("Exception occurred", exc_info=True)
        ################################################
        ## Backing up Site Devices Images
        for device in devices:
            _no_magic(backup, site["name"], device)
            message = f"Backing up {device['type'].upper()} {device['serial']} images"
            PB.log_message(message)
            try:
                i = 1
                while f"image{i}_url" in device:
                    url = device[f"image{i}_url"]
                    image_name = f"{FILE_PREFIX}_org_{org_id}_device_{device['serial']}_image_{i}.png"
                    urllib.request.urlretrieve(url, image_name)
                    i += 1
                PB.log_success(message, True)
            except Exception as e:
                PB.log_failure(message, True)
                LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ## End
    PB.log_title(f"Backup Done", end=True)
    print()


def _save_to_file(backup_data:dict,backup_file:str, backup_name:str, puk_path:str):
    backup_path = f"./org_backup/{backup_name}/"

    try:
        if puk_path:
            message = f"Saving to encrypted backup to {backup_path} "
            PB.log_title(message, end=True, display_pbar=False)
            eh = EncryptionHandler("./", backup_file)
            eh.encrypt_memory(json.dumps(backup_data), puk_path)
            PB.log_success(message, display_pbar=False)
        else:
            message = f"Saving to file {backup_path} "
            PB.log_title(message, end=True, display_pbar=False)
            with open(backup_file, "w") as f:
                json.dump(backup_data, f)
            PB.log_success(message, display_pbar=False)
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def _start_inventory_backup(
    mist_session: mistapi.APISession,
    org_id: str,
    org_name: str,
    backup_folder:str,
    backup_name:str,
    puk_path:str
):
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
    # PREPARE PROGRESS BAR
    try:
        device_count = 0
        for device_type in DEVICE_TYPES:
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                mist_session, org_id, type=device_type, limit=1
            )
            if response.headers.get("X-Page-Total"):
                device_count += int(response.headers.get("X-Page-Total"))
            else:
                device_count += len(response.data)
        response = mistapi.api.v1.orgs.sites.countOrgSites(
            mist_session, org_id, limit=1
        )
        if response.headers.get("X-Page-Total"):
            site_count = int(response.headers.get("X-Page-Total"))
        else:
            site_count = len(response.data)
        PB.set_steps_total(2 + len(DEVICE_TYPES) + site_count + device_count)
    except Exception as e:
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)

    backup = {
        "org": {
            "id": "",
            "sites": {},
            "old_sites_id": {},
            "old_deviceprofiles_id": {},
            "old_evpntopo_id": {},
            "magics": {},
            "devices": [],
            "devices_without_magic": [],
        }
    }
    _backup_inventory(mist_session, org_id, org_name, backup)
    _save_to_file(backup, BACKUP_FILE, backup_name, puk_path)
    if backup["org"]["devices_without_magic"]:
        console.warning(
            "It was not possible to retrieve the claim codes for the following devices:"
        )
        mistapi.cli.display_list_of_json_as_table(
            backup["org"]["devices_without_magic"],
            ["site", "device_type", "model", "name", "mac", "serial"],
        )
        print()


def start(
    mist_session: mistapi.APISession,
    org_id: str,
    backup_folder: str = None,
    backup_name:str=None,
    backup_name_date:bool=False,
    backup_name_ts:bool=False,
    puk_path:str=None
):
    """
    Start the backup process

    PARAMS
    -------
    dst_apisession : mistapi.APISession
        mistapi session with `Super User` access the destination Org, already logged in
    org_id : str
        org_id of the org to backup
    org_name : str
        Org name where to deploy the inventory. This parameter requires "org_id" to be defined
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created with the 
        org name). default is "./org_backup"
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

    """
    current_folder = os.getcwd()
    if not backup_folder:
        backup_folder = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    _start_inventory_backup(mist_session, org_id, org_name, backup_folder, backup_name, puk_path)
    os.chdir(current_folder)


#####################################################################
#### USAGE ####
def usage(error_message:str=None):
    """
    display usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup all the devices from an organization in AES encrypted
file.
It will backup the devices claim codes (if any), configuration (including
position on the maps) and  pictures.
You can use the script "org_inventory_deploy.py" to restore the generated backup 
files to an existing organization or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

The backup is AES encrypted with a randomly generated key. The encryption key
is stored in a RSA encrypted file (encrypted with a RSA public key). The RSA
Private key is required to be able to decrypt AES encryption key. 

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

The encrypted backup can be decrypted with the following script:
https://github.com/tmunzer/mist_library/blob/master/scripts/utils/encryption.py

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
python3 ./org_inventory_backup.py     
python3 ./org_inventory_backup.py \
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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:e:l:b:dtp:",
            ["help", "org_id=", "env=", "log_file=", "backup_folder=", "datetime", "timestamp", "puk="],
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
    start(APISESSION, ORG_ID, BACKUP_FOLDER, BACKUP_NAME, BACKUP_NAME_DATE, BACKUP_NAME_TS, PUK_PATH)
