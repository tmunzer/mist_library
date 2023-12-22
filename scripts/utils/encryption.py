"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to manage backup encryption.

This file can be used:
- to generate RSA Private and Public keys for encryption
- to encrypt file (AES encryption, AES key is RSA Protected)
- to decrypt file 

-------
Requirements:
pycryptodome: https://pypi.org/project/pycryptodome/

-------
Usage:
This script can be used for three different actions:

1. Generate RSA Key pair:
    Generate a Private and Public RSA key pair, and save them to a file. The process
    will ask for a password to protect the private key (optional)
    
    -------
    Required Paramaters:
    -g, --generate          enable the RSA Key pair generation process
    -p, --puk=              file path to save the RSA public key
    -P, --prk=              file path to save the RSA private key

    -------
    example:
    python3 ./encrypt.py -g -p ./rsa.pub -P ./rsa

2. Encrypt file:
    Encrypt a file with AES encryption. A unique AES encryption key will be generated for
    each use, and will be save in a file encrypted with the RSA public key.
    This will generate two files:
    - <backup_file>.enc: the AES encrypted backup file 
    - <backup_file>.key; the RSA encrypted AES encryption key

    -------
    Required Parameters:
    -e, --encrypt           enable the encryption process
    -b, --backup_folder=    folder path where the decrypted file is locate
    -f, --backup_file=      file name to encrypt
    -p, --puk=              path to the RSA public key

    -------
    example: 
    python3 ./encrypt.py -e -b ./path/to/the/backup -f backup.json -p ./rsa.pub

3. Decrypt file:
    Decrypt a file encrypted with this script. Will use the RSA Private key to decrypt the 
    AES encryption key, then decrypt the encrypted file.
    During the process, the RSA private key password will be asked (leave empty if none)

    -------
    Required Paramters:
    -d, --decrypt           enable the decryption process
    -b, --backup_folder=    folder path where the encrypted file is locate
    -f, --backup_file=      file name to decrypt
    -P, --prk=              path to the RSA private key

    -------
    example: 
    python3 ./encrypt.py -d -b ./path/to/the/backup7 -f backup.enc -P ./rsa

"""
import os
import sys
import json
import getopt
import getpass
from base64 import b64encode
from hashlib import sha256
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from Cryptodome.Random import get_random_bytes


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

def _rsa_prk_generation(prk_path:str, secret_code:str):
    key = RSA.generate(2048)
    encrypted_key = key.export_key(passphrase=secret_code, pkcs=8,
                                protection="scryptAndAES128-CBC")
    with open(prk_path, "wb") as f:
        f.write(encrypted_key)

def _rsa_puk_generation(prk_path:str, puk_path:str, secret_code:str):
    encoded_key = open(prk_path, "rb").read()
    key = RSA.import_key(encoded_key, passphrase=secret_code)
    with open(puk_path, "wb") as f:
        f.write(key.publickey().export_key())

def generate_rsa_keys(prk_path:str, puk_path:str):
    """
    Function to generate RSA key pair

    PARAMS
    -------
    prk_path : str
        file path to save the RSA Public key
    puk_path : str
        file path to save the RSA Private key
    """

    secret_code = None
    secret_code_validation = "x"
    while secret_code != secret_code_validation:
        secret_code = getpass.getpass("Private Key Password (empty for none): ")
        if len(secret_code) == 0:
            secret_code = None
            secret_code_validation = None
        else:
            secret_code_validation = getpass.getpass("Re-type the Private Key Password: ")
        if secret_code != secret_code_validation:
            print()
            print("Error: passwords do not match")

    _rsa_prk_generation(prk_path, secret_code)
    _rsa_puk_generation(prk_path, puk_path, secret_code)

def usage(error_message: str = None):
    """print script usage"""
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script manage encryption of the generated files.

This file can be used:
- to generate RSA Private and Public keys for encryption
- to encrypt file (AES encryption, AES key is RSA Protected)
- to decrypt file 

-------
Requirements:
pycryptodome: https://pypi.org/project/pycryptodome/

-------
Usage:
This script can be used for three different actions:

1. Generate RSA Key pair:
    Generate a Private and Public RSA key pair, and save them to a file. The process
    will ask for a password to protect the private key (optional)
    
    -------
    Required Paramaters:
    -g, --generate          enable the RSA Key pair generation process
    -p, --puk=              file path to save the RSA public key
    -P, --prk=              file path to save the RSA private key

    -------
    example:
    python3 ./encrypt.py -g -p ./rsa.pub -P ./rsa

2. Encrypt file:
    Encrypt a file with AES encryption. A unique AES encryption key will be generated for
    each use, and will be save in a file encrypted with the RSA public key.
    This will generate two files:
    - <backup_file>.enc: the AES encrypted backup file 
    - <backup_file>.key; the RSA encrypted AES encryption key

    -------
    Required Parameters:
    -e, --encrypt           enable the encryption process
    -b, --backup_folder=    folder path where the decrypted file is locate
    -f, --backup_file=      file name to encrypt
    -p, --puk=              path to the RSA public key

    -------
    example: 
    python3 ./encrypt.py -e -b ./path/to/the/backup -f backup.json -p ./rsa.pub

3. Decrypt file:
    Decrypt a file encrypted with this script. Will use the RSA Private key to decrypt the 
    AES encryption key, then decrypt the encrypted file.
    During the process, the RSA private key password will be asked (leave empty if none)

    -------
    Required Paramters:
    -d, --decrypt           enable the decryption process
    -b, --backup_folder=    folder path where the encrypted file is locate
    -f, --backup_file=      file name to decrypt
    -P, --prk=              path to the RSA private key

    -------
    example: 
    python3 ./encrypt.py -d -b ./path/to/the/backup7 -f backup.enc -P ./rsa

""")
    if error_message:
        print(f"ERROR: {error_message}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hedgb:f:p:P:",
            [
                "help",
                "encrypt",
                "decrypt",
                "generate",
                "backup_folder=",
                "backup_file_name=",
                "puk=",
                "prk=",                
            ],
        )
    except getopt.GetoptError as err:
        print(err)
        usage()

    ACTION = None
    BACKUP_FOLDER = None
    BACKUP_FILE_NAME = None
    PUK_PATH = None
    PRK_PATH = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-e", "--encrypt"]:
            if not ACTION:
                ACTION = "encrypt"
            else:
                usage(
                    "Invalid parameters: "
                    '"-e"/"--encrypt", "-d"/"--decrypt" '
                    'and "-g"/"--generate" are esclusive'
                )
        elif o in ["-d", "--decrypt"]:
            if not ACTION:
                ACTION = "decrypt"
            else:
                usage(
                    "Invalid parameters: "
                    '"-e"/"--encrypt", "-d"/"--decrypt" '
                    'and "-g"/"--generate" are esclusive'
                )
        elif o in ["-g", "--generate"]:
            if not ACTION:
                ACTION = "generate"
            else:
                usage(
                    "Invalid parameters: "
                    '"-e"/"--encrypt", "-d"/"--decrypt" '
                    'and "-g"/"--generate" are esclusive'
                )
        elif o in ["-b", "--backup_folder"]:
            BACKUP_FOLDER = a
        elif o in ["-f", "--backup_file_name"]:
            BACKUP_FILE_NAME = a
        elif o in ["-p", "--puk"]:
            PUK_PATH = a
        elif o in ["-P", "--prk"]:
            PRK_PATH = a

    if ACTION == "encrypt":
        if not PUK_PATH:
            usage(
                'Invalid parameters: "-p"/"--puk" parameter is required for encyption'
            )
        elif not BACKUP_FOLDER:
            usage(
                'Invalid parameters: "-b"/"--backup_folder" parameter is required for encyption'
            )
        elif not BACKUP_FILE_NAME:
            usage(
                'Invalid parameters: "-f"/"--backup_file_name" parameter is required for encyption'
            )
        else:
            EH = EncryptionHandler(BACKUP_FOLDER, BACKUP_FILE_NAME)
            EH.encrypt_file(PUK_PATH)

    elif ACTION == "decrypt":
        if not PRK_PATH:
            usage(
                'Invalid parameters: "-P"/"--prk" parameter is required for decryption'
            )
        elif not BACKUP_FOLDER:
            usage(
                'Invalid parameters: "-b"/"--backup_folder" parameter is required for decryption'
            )
        elif not BACKUP_FILE_NAME:
            usage(
                'Invalid parameters: "-f"/"--backup_file_name" parameter is required for decryption'
            )
        else:
            EH = EncryptionHandler(BACKUP_FOLDER, BACKUP_FILE_NAME)
            EH.decrypt_file(PRK_PATH)

    elif ACTION == "generate":
        if not PUK_PATH:
            usage(
                'Invalid parameters: "-p"/"--puk" parameter is required for RSA Key generation'
            )
        elif not PRK_PATH:
            usage(
                'Invalid parameters: "-P"/"--prk" parameter is required for RSA Key generation'
            )
        else:
            generate_rsa_keys(PRK_PATH, PUK_PATH)

    else:
        usage(
            'Invalid parameters: either "-g"/"--generate", '\
            '"-e"/"--encrypt", "d"/"--decrypt" are required'
            )
