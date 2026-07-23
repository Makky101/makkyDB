from transaction_manager import valuePointer,logical
from operator import attrgetter


# a small class that holds just the key and the valuepointer
class DataNode:
    def __init__(self,id_num,valuePointer):
        self.id = id_num
        self.vp = valuePointer

    @property
    def packed_data(self):
        return (self.id,self.vp._address)

class NodePointer(valuePointer):
    def store_child_pointers(self, storage):
        """Persist child objects for a node pointer that still has RAM data."""
        if self.memory_object:
            self.memory_object.store_children(storage)

    @staticmethod
    def fetch_ram_object(data):
        object_data = data[1]
        data_arr = []
        children_pointers = []
        leaf = False

        key_count = object_data[0]

        start,finish = 1, key_count + 1
        for i in range(start,finish):
            data_node = DataNode(object_data[i][0],valuePointer(address=object_data[i][1]))
            data_arr.append(data_node)

        children_count = object_data[key_count+1]

        start,finish = key_count+2,key_count+2+children_count
        for i in range(start,finish):
            node_pointer = NodePointer(address=object_data[i]) 
            children_pointers.append(node_pointer)

        leaf = object_data[-1]
        
        B_data = BTreeNode(
            data_arr=data_arr,
            children=children_pointers,
            leaf=leaf
        )
        metadata = data[0] 
        return (metadata,B_data)

    def get_object(self,storage):
        """Load the object from disk when needed and cache it in memory."""
        if self.memory_object is None and self.address:
            self.meta_data, self.memory_object = self.fetch_ram_object(
                storage.read_from_disk(
                    self.address,
                    ["NODE"]   
                )
            )# I explicitly set to Node and yes I write my code by hand with my own logic
            # so it is not pretty 🥀
        
        return self.memory_object

    @staticmethod
    def ingest_ram_object(meta_data,object_string):
        """Serialize a BinaryNode"""
        # key count,keys,children count,children,leaf
        package = []
        package.append(len(object_string.data))
        package.extend([node.packed_data for node in object_string.data])
        package.append(len(object_string.children))
        package.extend([node_pointer._address for node_pointer in object_string.children])
        package.append(object_string.leaf)
        payload = (meta_data,package)

        return payload

class BTreeNode:
    degree = 5
    max_data = degree - 1
    min_data = (max_data) / 2
    node_pointer = NodePointer
    
    
    def __init__(self,leaf=False,data_arr=None,children=None):
        """Hold a max of 4 data_nodes and a min of 2 data_nodes plus pointers to its value except for the root node"""
        self.data = data_arr if data_arr else  []
        self.leaf = True if  not children else leaf
        self.children = children if children else []

    def add_data(self,data_node,storage):
        # we have reached the bottom
        if self.leaf:
            self.data.append(data_node)
            self.data.sort(key=attrgetter("id"))
            return self.leak(self.leaf)
        else:
            # recursively go down the root if it is not at the botto
            position = 0
            while position < len(self.data) and data_node.id > self.data[position].id:
                position += 1
            result = self.children[position].get_object(storage).add_data(data_node,storage)
            if result is None:
                return None
            
            self.absorb(result,position)

            return self.leak(self.leaf)

    # run when one of the child has separated to absorb the separator and handle children
    def absorb(self,result,position):
        separator,left_data,right_data = result
        self.data.insert(position,separator[0])
        self.children[position]=left_data 
        self.children.insert(position+1,right_data)
        
    # decides if we should split or not:
    def leak(self,leaf):
        if len(self.data) > self.max_data:
            return self.split(leaf)
        else:
            return None

    def split(self,leaf):
        left_data = self.node_pointer(
            meta_data=['NODE'],
            memory_object=BTreeNode(
                leaf=leaf,
                data_arr=self.data[:2],
                children=self.children[:3] if self.children else []
            )
        )
        right_data = self.node_pointer(
            meta_data=['NODE'],
            memory_object=BTreeNode(
                leaf=leaf,
                data_arr=self.data[3:],
                children=self.children[3:] if self.children else []
            )
        )
        separator = [self.data[2]]
        return (separator,left_data,right_data)
    

    def store_children(self,storage):
        """Persist this node's value and child nodes before storing the node."""
        self.valuePointer.store_object(storage)
        self.rightPointer.store_object(storage)
        self.leftPointer.store_object(storage)

    @classmethod
    def copy_node(cls,node,**kwargs):
        """Return a copy of a node with selected fields replaced."""
        return cls(
            key=kwargs.get('key',node.key),
            rightPointer=kwargs.get('rightPointer',node.rightPointer),
            leftPointer=kwargs.get('leftPointer',node.leftPointer),
            valuePointer=kwargs.get('valuePointer',node.valuePointer)
        )


class BTree(logical):
    node_pointer = NodePointer
    data_node = DataNode
    btree_node = BTreeNode

    def read(self,key,node):
        """Search the binary tree for a key and return its stored value."""
        while node:
            if key < node.key:
                node = self.traverse(node.leftPointer)
            elif node.key < key:
                node = self.traverse(node.rightPointer)
            else:
                return self.traverse(node.valuePointer)
        return None

    def update(self,storage,root=None,data_node=None):
        """Insert or replace a key by returning a new node pointer path."""
        if root is None:
            new_root = self.btree_node(data_arr=[data_node])
            return self.node_pointer(memory_object=new_root)
        
        result = root.add_data(data_node,storage)
        if result is None:
            return self.node_pointer(memory_object=root)
        
        separator, left_data, right_data = result
        new_root =  self.btree_node(
            data_arr=separator,
            children=[left_data,right_data]
        )

        return self.node_pointer(memory_object=new_root)

    def remove(self,node,key):
        """Delete a key and return the replacement subtree pointer."""
        if node is None:
            raise KeyError(key)

        if key < node.key:
            return self.node_pointer(
                memory_object=self.btree_node.copy_node(
                    node=node,
                    leftPointer=self.remove(
                        self.traverse(node.leftPointer),
                        key
                    )
                )
            )

        if node.key < key:
            return self.node_pointer(
                memory_object=self.btree_node.copy_node(
                    node=node,
                    rightPointer=self.remove(
                        self.traverse(node.rightPointer),
                        key
                    )
                )
            )

        left = self.traverse(node.leftPointer)
        right = self.traverse(node.rightPointer)

        if left and right:
            successor, new_right = self.pop_min(node.rightPointer)
            return self.node_pointer(
                memory_object=self.btree_node.copy_node(
                    node=successor,
                    leftPointer=node.leftPointer,
                    rightPointer=new_right
                )
            )
        
        if left is None:
            return node.rightPointer
        
        if right is None:
            return node.leftPointer

