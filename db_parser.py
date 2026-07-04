from storage_engine import storage
from data_structure import Tree


class API:
    """Acts as the API between the user interface and the core logic."""

    def __init__(self, file_obj):
        """Create the storage layer and load the tree wrapper for the file."""
        self.storage = storage(file_obj)
        self.tree = Tree(self.storage)

    def __setitem__(self, key, value):
        """Assign a value to a key in memory; call stamp() to persist it."""
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
