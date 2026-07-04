class valuePointer:
    def __init__(self,memory_object=None,address=0):
        """Point to either an in-memory object or an object stored on disk."""
        self.address = address
        self.memory_object = memory_object

    def store_child_pointers(self,storage):
        """Stores child pointers before this object is stored."""
        pass

    # serializes ram object to bytes
    @staticmethod
    def ram_object_to_bytes(object_string):
        """Convert a string value from memory into bytes for disk storage."""
        return object_string.encode('utf-8')
    
    # deserializes bytes to ram object
    @staticmethod
    def bytes_to_ram_object(byte_string):
        """Convert stored bytes back into a string value."""
        return byte_string.decode('utf-8')

    @property
    def _address(self):
        """Expose the disk address used when serializing node pointers."""
        return self.address
 
    # get the actual value from disk
    def get_object(self,storage):
        """Load the object from disk when needed and cache it in memory."""
        if self.memory_object is None and self.address:
            self.memory_object = self.bytes_to_ram_object(
                storage.read_from_disk(self.address)
            )
        return self.memory_object

    # store value to disk
    def store_object(self,storage):
        """Write an in-memory object to disk if it has no address yet."""
        if self.memory_object is not None and not self.address:
            self.store_child_pointers(storage)
            self.address = storage.write_to_disk(
                self.ram_object_to_bytes(self.memory_object)
            )

class logical:
    """
    Abstract base class providing the transactional and structural logic 
    for an on-disk data structure (like a B+ Tree).
    """
    node_pointer = None
    value_pointer = valuePointer
    def __init__(self,storage):
        """Attach storage and load the current root pointer from disk."""
        self.storage = storage
        self.dirty = False
        self.reload_tree_pointer()

    def reload_tree_pointer(self):
        """Refresh the root pointer from the address in the metablock."""
        self.tree_pointer = self.node_pointer(
            address=self.storage.get_root_address()
        )

    def retrieve(self,key):
        """Read a key from the current tree, reloading disk state if clean."""
        if not self.dirty:
            self.reload_tree_pointer()
        value = self.read(key,self.traverse(self.tree_pointer))
        if value is None:
            raise KeyError(key)
        return value
    
    def stamp(self):
        """Persist pending changes and store the latest root address."""
        self.storage.lock_for_process()
        self.tree_pointer.store_object(self.storage)
        self.storage.stamp_root_address(self.tree_pointer._address)
        self.dirty = False

    def assign(self,key,value):
        """Apply an in-memory insert or update and mark the tree dirty."""
        if not self.dirty:
            self.reload_tree_pointer()
        self.tree_pointer = self.update(
            self.traverse(self.tree_pointer),
            key,
            self.value_pointer(memory_object=value)
        )
        self.dirty = True

    def delete(self,key):
        """Apply an in-memory delete and mark the tree dirty."""
        if not self.dirty:
            self.reload_tree_pointer()
        try:
            self.tree_pointer = self.remove(
                self.traverse(self.tree_pointer),
                key
            )
        except KeyError:
            raise
        self.dirty = True

    def traverse(self,pointer):
        """Resolve a pointer into the object it references."""
        return pointer.get_object(self.storage)
