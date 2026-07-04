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
        """Ensure the file begins with the reserved metadata block."""
        self.lock_for_process()
        self.move_to_end()
        end_address = self.file_obj.tell()
        if end_address < self.METABLOCK_SIZE:
            self.file_obj.write(b'\x00' * (self.METABLOCK_SIZE - end_address))
        self.unlock()

    # a read only property to check if it is locked
    @property
    def is_locked(self):
        """Return whether this storage object currently holds the file lock."""
        return self.locked

    # locks the file object if not
    def lock_for_process(self):
        """Acquire an exclusive lock before writing to the database file."""
        if not self.locked:
            self.file_obj.seek(0)
            portalocker.lock(self.file_obj,portalocker.LOCK_EX)
            self.locked = True
            return self.locked
        return False

    def lock(self):
        """Backward-compatible wrapper around lock_for_process()."""
        return self.lock_for_process()

    # unlocks the file object
    def unlock(self):
        """Flush data, release the file lock, and refresh the file handle."""
        if self.locked:
            self.file_obj.flush()
            self.file_obj.seek(0)
            portalocker.unlock(self.file_obj)
            self.locked = False
            file_name = getattr(self.file_obj, "name", None)
            if isinstance(file_name, str):
                self.file_obj.close()
                self.file_obj = open(file_name, "r+b")

    # moves cursor to the end of the file
    def move_to_end(self):
        """Move the file cursor to the end before appending data."""
        self.file_obj.seek(0,2)

    # moves cursor to where the metablock space is
    def move_to_metablock(self):
        """Move the file cursor to the metadata/root-address area."""
        self.file_obj.seek(0)
        
    # converts a numerical value to an unsigned 64 bit integer
    def integer_to_bytes(self,integer):
        """Pack an integer as an unsigned 64-bit big-endian byte string."""
        return struct.pack(self.INTEGER_FORMAT,integer)
    
    # converts an unsigned 64 bit integer to a numerical value 
    def bytes_to_integer(self,bytes):
        """Unpack an unsigned 64-bit big-endian byte string into an integer."""
        return struct.unpack(self.INTEGER_FORMAT,bytes)[0]

    # writes the length of the serialized object data to disk
    def write_integer(self,integer):
        """Write an encoded integer at the current file cursor."""
        self.file_obj.write(self.integer_to_bytes(integer))

    # returns the deserialized object data from disk
    def read_integer(self):
        """Read and decode an integer from the current file cursor."""
        return self.bytes_to_integer(self.file_obj.read(self.INTEGER_LENGTH))
    
    # reads raw binary data from disk
    def read_from_disk(self,obj_address):
        """Read a length-prefixed binary object from a disk address."""
        self.file_obj.seek(obj_address)
        byte_length = self.read_integer()
        binary_data = self.file_obj.read(byte_length)
        return binary_data

    # writes raw binary data to disk
    def write_to_disk(self,binary_data):
        """Append a length-prefixed binary object and return its address."""
        self.lock_for_process()
        self.move_to_end()
        obj_address = self.file_obj.tell()
        self.write_integer(len(binary_data))
        self.file_obj.write(binary_data)
        return obj_address
    
    # commit root address to file
    def stamp_root_address(self,address):
        """Store the latest committed root address in the metablock."""
        self.lock_for_process()
        self.file_obj.flush()
        self.move_to_metablock()
        self.write_integer(address)
        self.file_obj.flush()
        self.unlock()

    def commit_root_address(self,address):
        """Backward-compatible wrapper around stamp_root_address()."""
        self.stamp_root_address(address)

    # gets root address from the file
    def get_root_address(self):
        """Read the current committed root address from the metablock."""
        self.move_to_metablock()
        root_address = self.read_integer()
        return root_address
    
    @property
    def is_closed(self):
        """Return whether the underlying file object has been closed."""
        return self.file_obj.closed
