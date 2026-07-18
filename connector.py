from db_parser import API
import os


class connect:
    def plug(dbName="storage.mdb"):
        """Open an existing database file or create it, then return the API."""
        try:
            file_obj = open(dbName, "r+b")
        except IOError:
            # Had to remove os.O_BINARY it only works for windows
            file_desc = os.open(dbName, flags=os.O_CREAT | os.O_RDWR)
            file_obj = os.fdopen(file_desc, "r+b")
        return API(file_obj)
