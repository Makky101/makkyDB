class valuePointer:
    def __init__(self,memory_object=None,address=0,meta_data=None):
        """
        Initialize a pointer to an in-memory object or an object stored on disk.
        
        Parameters:
            memory_object: Optional in-memory object referenced by the pointer.
            address: Disk address of the referenced object.
            meta_data: Metadata used to describe the stored object.
        """
        self.address = address
        self.memory_object = memory_object if memory_object else None
        self.meta_data = meta_data if meta_data else []

    

    def store_child_pointers(self,storage):
        """Stores child pointers before this object is stored."""
        pass

    # serializes ram object to bytes
    @staticmethod
    def ingest_ram_object(meta_data,object_data):
        """
        Convert metadata-described in-memory values into disk-serializable values.
        
        Parameters:
            meta_data (list): Type descriptors for the corresponding values.
            object_data (list): Values to serialize; text values are encoded as UTF-8 bytes and number values are converted to integers in place.
        
        Returns:
            tuple: The metadata and serialized object data as a tuple.
        """
        for i in range(len(meta_data) - 1,-1,-1):
            if meta_data[i] == 'TEXT' or meta_data[i] == 'LONGTEXT':
                binary_data = object_data[i].encode('utf-8')
                object_data[i] = (len(binary_data),binary_data)

            elif meta_data[i] == 'NUMBER':
                object_data[i] = int(object_data[i],10)

        payload = (meta_data,object_data)
        return payload


    # deserializes bytes to ram object
    @staticmethod
    def fetch_ram_object(data):
        """
        Return the provided data unchanged.
        
        Parameters:
            data: The data to return.
        
        Returns:
            The same data object provided as input.
        """
        return data

    @property
    def _address(self):
        """Expose the pointer's disk address."""
        return self.address
 
    # get the actual value from disk
    def get_object(self,storage):
        """Load the object from disk when needed and cache it in memory."""
        if self.memory_object is None and self.address:
            self.memory_object = self.fetch_ram_object(
                storage.read_from_disk(
                    self.address,
                    self.meta_data
                )
            )
        
        return self.memory_object

    # store value to disk
    def store_object(self,storage):
        """Write an in-memory object to disk if it has no address yet."""
        if self.memory_object is not None and not self.address:
            self.store_child_pointers(storage)
            self.address = storage.write_to_disk(
                self.ingest_ram_object(self.meta_data,self.memory_object)
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
            self.storage,
            self.traverse(self.tree_pointer),
            self.data_node(
                key,
                self.value_pointer(memory_object=value)
            )
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
