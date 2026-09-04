"""Generate the Grimoire master RSA-2048 keypair.

Run once per environment; paste the output into backend/.env. Never commit
MASTER_PRIVATE_KEY_D to git or store it in the database.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_core.rsa import generate_keypair  # noqa: E402


def main():
    pub, priv = generate_keypair(2048)
    print("# Paste into backend/.env. Keep MASTER_PRIVATE_KEY_D secret, never commit it.")
    print(f"MASTER_PUBLIC_KEY_N={pub.n}")
    print(f"MASTER_PUBLIC_KEY_E={pub.e}")
    print(f"MASTER_PRIVATE_KEY_D={priv.d}")


if __name__ == "__main__":
    main()
