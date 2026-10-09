import base64
import hashlib
import hmac
import os
import sys

SCRAM_ITERATIONS = 4096


def scram_verifier(password):
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, SCRAM_ITERATIONS)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    encoded_salt, encoded_stored_key, encoded_server_key = [base64.b64encode(part).decode() for part in (salt, stored_key, server_key)]

    return "$".join(
        [
            "SCRAM-SHA-256",
            "{}:{}".format(SCRAM_ITERATIONS, encoded_salt),
            "{}:{}".format(encoded_stored_key, encoded_server_key),
        ]
    )


def completion_mark(nonce):
    return "rp-" + hashlib.md5(nonce.encode()).hexdigest()


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "scram-verifier":
        print(scram_verifier(sys.stdin.read()))
    elif command == "completion-mark" and len(sys.argv) == 3:
        print(completion_mark(sys.argv[2]))
    else:
        sys.exit(2)


main()
