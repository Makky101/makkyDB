from db_parser import API
import os


class connect:
    def plug(dbName="storage.mdb"):
        """
        Open a database file for read/write access, creating it if necessary.
        
        Parameters:
            dbName (str): Path to the database file.
        
        Returns:
            API: An API instance wrapping the opened database file.
        """
        try:
            file_obj = open(dbName, "r+b")
        except IOError:
            # Had to remove os.O_BINARY it only works for windows
            file_desc = os.open(dbName, flags=os.O_CREAT | os.O_RDWR)
            file_obj = os.fdopen(file_desc, "r+b")
        return API(file_obj)
