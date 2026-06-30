import struct
import portalocker

class storage:
    METABLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    def __init__(self,file_obj):
        """holds the file object, 
        sets a boolean value to locked
        and ensures there is a metablock space"""

        self.file_obj = file_obj
        self.locked = False
        self.validate_metablock()

    # Ensures there is a metablock space
    def validate_metablock(self):
        self.lock()
        self.move_to_end()
        end_address = self.file_obj.tell()
        if end_address < self.METABLOCK_SIZE:
            self.file_obj.write(b'\x00' * (self.METABLOCK_SIZE - end_address))
        self.unlock()

    # locks the file object if not
    def lock(self):
        if not self.locked:
            portalocker.lock(self.file_obj,portalocker.LOCK_EX)
        self.locked = True

    # unlocks the file object
    def unlock(self):
        self.file_obj.flush()
        portalocker.unlock(self.file_obj)
        self.locked = False

    # moves cursor to the end of the file
    def move_to_end(self):
        self.file_obj.seek(0,2)

    # moves cursor to where the metablock space is
    def move_to_metablock(self):
        self.file_obj.seek(0)
        
    # converts a numerical value to an unsigned 64 bit integer
    def integer_to_bytes(self,integer):
        return struct.pack(self.INTEGER_FORMAT,integer)
    
    # converts an unsigned 64 bit integer to a numerical value 
    def bytes_to_integer(self,bytes):
        return struct.unpack(self.INTEGER_FORMAT,bytes)[0]

    # writes the length of the serialized object data to disk
    def write_integer(self,integer):
        self.file_obj.write(self.integer_to_bytes(integer))

    # returns the deserialized object data from disk
    def read_integer(self):
        return self.bytes_to_integer(self.file_obj.read(self.INTEGER_LENGTH))
    
    # reads raw binary data from disk
    def read_from_disk(self,obj_address):
        self.file_obj.seek(obj_address)
        byte_length = self.read_integer()
        binary_data = self.file_obj.read(byte_length)
        return binary_data

    # writes raw binary data to disk
    def write_to_disk(self,binary_data):
        self.lock()
        try:
            self.move_to_end()
            obj_address = self.file_obj.tell()

            self.write_integer(len(binary_data))
            self.file_obj.write(binary_data)

            self.unlock()
            return obj_address
        finally:
            self.unlock()
    
    # commit root address to file
    def commit_root_address(self,address):
        self.lock()
        self.file_obj.flush()
        self.move_to_metablock()
        self.write_integer(address)
        self.file_obj.flush()
        self.unlock()

    # gets root address from the file
    def get_root_address(self):
        self.move_to_metablock()
        root_address = self.read_integer()
        return root_address
    
    @property
    def is_closed(self):
        return self.file_obj.closed