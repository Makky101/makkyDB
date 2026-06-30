from storage_engine import storage
from data_structure import Tree

class API:
    """acts a the API between the user interface and the core underlying logic"""
    def __init__(self,file_obj):
        self.storage = storage(file_obj)
        self.tree = Tree(self.storage)
        
    # sets key to value  
    def __setitem__(self, key, value):
        if self.storage.is_closed:
            raise ValueError('Storage is closed')
        return self.tree.set(key,value)