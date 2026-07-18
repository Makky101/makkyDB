from storage_engine import storage
from data_structure import BTree


class API:
    """Acts as the API between the user interface and the core logic."""

    def __init__(self, file_obj):
        """
        Initialize storage and an in-memory tree backed by the provided file object.
        
        Parameters:
            file_obj: File object used for persistent storage.
        """
        self.storage = storage(file_obj)
        self.tree = BTree(self.storage)

    def __setitem__(self, key, value):
        """
        Assign a value to a key in the in-memory tree.
        
        Raises:
            ValueError: If the storage is closed.
        """
        if self.storage.is_closed:
            raise ValueError("Storage is closed")
        return self.tree.assign(key, value)

    def __getitem__(self, key):
        """Return the value stored under a key, or raise KeyError."""
        if self.storage.is_closed:
            raise ValueError("Storage is closed")
        return self.tree.retrieve(key)

    def __delitem__(self, key):
        """Remove a key in memory; call stamp() to persist the deletion."""
        if self.storage.is_closed:
            raise ValueError("Storage is closed")
        return self.tree.delete(key)

    def stamp(self):
        """Write pending tree changes to disk and update the root pointer."""
        if self.storage.is_closed:
            raise ValueError("Storage is closed")
        self.tree.stamp()
