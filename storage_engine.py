import struct
import portalocker

class storage:
    METABLOCK_SIZE = 4096
    BINARY_FORMAT = {
        'NODE':"!Q",
        'TEXT': "!H",
        'NUMBER':"!I",
        'LONGTEXT': "!I",
        'BOOLEAN': "!?"
    }
    BINARY_LENGTH = {
        'BOOLEAN': 1,
        'NUMBER': 4,
        'TEXT': 2,
        'LONGTEXT': 4,
        'NODE': 8
    }

    def __init__(self,file_obj,metadata):
        """holds the file object, 
        sets a boolean value to locked
        and ensures there is a metablock space"""

        self.file_obj = file_obj
        self.locked = False
        self.validate_metablock()
        self.validate_metadata(metadata)


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

    # locate the metaspace
    def seek_metaspace(self):
        self.file_obj.seek(4)

    # ensure meta_data in header the NODE type will be explicitly held in pointer
    def validate_metadata(self,metadata):
        self.seek_metaspace()
        meta_list = ['TEXT'] * len(metadata)
        binary_data = self.construct_binary_data(meta_list,self.BINARY_FORMAT,metadata,extra_data=True)
        self.file_obj.write(binary_data)
    
    def read_metadata(self):
        self.seek_metaspace()
        data_length = self.read_binary_length()
        binary_length = self.read_binary_length()
        binary_data = self.file_obj.read(binary_length)
        meta_list = ["TEXT"] * data_length
        metadata =  self.deconstruct_binary_data(meta_list,self.BINARY_LENGTH,self.BINARY_FORMAT,binary_data)
        return metadata


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
        
    
    # reads raw binary data from disk
    def read_from_disk(self,obj_address,meta_data):
        """Read a length-prefixed binary object from a disk address."""
        if not meta_data:
            self.meta_data = self.read_metadata()
        self.file_obj.seek(obj_address)
        binary_length = struct.unpack(self.BINARY_FORMAT['NUMBER'], self.file_obj.read(4))[0]
        data_list = self.deconstruct_binary_data(
            self.meta_data,
            self.BINARY_LENGTH,
            self.BINARY_FORMAT,
            self.file_obj.read(binary_length)
        )
        return data_list

    # construct binary format
    @staticmethod
    def construct_binary_data(meta_data,binary_format,object_data,extra_data=False):
        binary_data = b''
        if 'NODE' in meta_data:
            binary_data = object_data
        else:
            for data in range(len(meta_data)):
                if meta_data[data] == "TEXT" or meta_data[data] == "LONGTEXT":
                    binary_data += struct.pack(binary_format[data],object_data[data][0])
                    binary_data += object_data[data][1]
                elif meta_data[data] == "BOOLEAN":
                    binary_data += struct.pack(binary_format[data],object_data[data])
                elif meta_data[data] == "NUMBER":
                    binary_data += struct.pack(binary_format[data],object_data[data])
            
        binary_length = struct.pack(binary_format["NUMBER"],len(binary_data))
        if extra_data:
            data_length = struct.pack(binary_format["NUMBER"],len(object_data))
            binary_data = data_length + binary_length + binary_data
        else:
            binary_data = binary_length + binary_data

        return binary_data

    # deconstruct binary format
    @staticmethod
    def deconstruct_binary_data(meta_data,binary_length,binary_format,binary_data):
        result = []
        offset1 = offset2 = 0
        for data in meta_data:
            if data == "TEXT" or data == "LONGTEXT":
                offset2 += binary_length[data]
                text_length = struct.unpack(binary_format[data],binary_data[offset1:offset2])[0]
                offset1 = offset2
                offset2 += text_length
                text_data = binary_data[offset1:offset2].decode('utf-8')
                result.append(text_data)
                offset1 = offset2
            elif data == "NUMBER":
                offset2 += binary_length[data]
                number = struct.unpack(binary_format[data],binary_data[offset1:offset2])[0]
                offset1 = offset2
                result.append(number)
            elif data == "BOOLEAN":
                offset2 += binary_length[data]
                boolean = struct.unpack(binary_format[data],binary_data[offset1:offset2])[0]
                offset1 = offset2
                result.append(boolean)
        
        return result


    # writes raw binary data to disk
    def write_to_disk(self,payload):
        """Append a length-prefixed binary object and return its address."""
        self.lock_for_process()
        metadata, values = payload
        self.move_to_end()
        obj_address = self.file_obj.tell()
        binary_data = self.construct_binary_data(metadata,self.BINARY_FORMAT,values)
        self.file_obj.write(binary_data)
        return obj_address
    
    # commit root address to file
    def stamp_root_address(self,address):
        """Store the latest committed root address in the metablock."""
        self.lock_for_process()
        self.file_obj.flush()
        self.move_to_metablock()
        binary_data = self.construct_binary_data(
            ['NUMBER'],
            self.BINARY_FORMAT,
            [address]
        )
        self.file_obj.write(binary_data)
        self.file_obj.flush()
        self.unlock()

    def commit_root_address(self,address):
        """Backward-compatible wrapper around stamp_root_address()."""
        self.stamp_root_address(address)

    def read_binary_length(self):
        binary_length = struct.unpack(self.BINARY_FORMAT['NUMBER'],self.file_obj.read(4))[0]
        return binary_length

    # gets root address from the file
    def get_root_address(self):
        """Read the current committed root address from the metablock."""
        self.move_to_metablock()
        binary_length = self.read_binary_length()
        root_address = self.deconstruct_binary_data(
            ['NUMBER'],
            self.BINARY_LENGTH,
            self.BINARY_FORMAT,
            self.file_obj.read(binary_length)
        )
        return root_address
    
    @property
    def is_closed(self):
        """Return whether the underlying file object has been closed."""
        return self.file_obj.closed
