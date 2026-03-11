"""Module entrypoint for `python -m file_mcp_server`.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: Entrypoint shim that forwards to `file_mcp_server.main:main`.
"""

from .main import main

if __name__ == "__main__":
    main()
