from storage_engine import storage

class valuePointer:
    def __init__(self,memory_object=None,address=0):
        self.address = address
        self.memory_object = memory_object

    def store_pointers():
        """I dont know what goes in here yet"""
        pass

    # serializes ram object to bytes
    @staticmethod
    def ram_object_to_bytes(object_string):
        return object_string.encode('utf-8')
    
    # deserializes bytes to ram object
    @staticmethod
    def bytes_to_ram_object(byte_string):
        return byte_string.decode('utf-8')
 
    # get the actual value from disk
    def get_object(self,storage):
        pass



class logical:
    """
    Abstract base class providing the transactional and structural logic 
    for an on-disk data structure (like a B+ Tree).
    """
    node_pointer = None
    value_pointer = valuePointer
    def __init__(self,storage):
        self.storage = storage
        self.reload_tree_pointer()

    def reload_tree_pointer(self):
        self.tree_pointer = self.node_pointer(
            address=self.storage.get_root_address()
        )


    def set(self,key,value):
        pass
