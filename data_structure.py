from transaction_manager import valuePointer,logical
from operator import attrgetter
import pickle


# a small class that holds just the key and the valuepointer
class DataNode:
    def __init__(self,id_num,valuePointer):
        self.ID = id_num
        self.vp = valuePointer

class BTreeNode:
    degree = 5
    max_data = degree - 1
    min_data = (max_data) / 2
    def __init__(self,leaf=False,arr=None,children=None):
        """Hold a max of 4 data_nodes and a min of 2 data_nodes plus pointers to its value except for the root node"""
        self.data = arr if arr else  []
        self.leaf = leaf
        self.children = children if children else []

    def add_data(self,data_node):
        # we have reached the bottom
        if self.leaf:
            self.data.append(data_node)
            self.data.sort(key=attrgetter("ID"))
            return self.leak(self.leaf)
        else:
            # recursively go down the root if it is not at the botto
            position = 0
            while position < len(self.data) and data_node.ID > self.data[position].ID:
                position += 1
            result = self.children[position].add_data(data_node)
            if result is None:
                return None
            
            self.absorb(result,position)

            return self.leak(self.leaf)

    # run when one of the child has separated to absorb the separator and handle children
    def absorb(self,result,position):
        separator,left,right = result
        self.data.insert(position,separator)
        self.children[position]=left 
        self.children.insert(position+1,right)
        
    # decides if we should split or not:
    def leak(self,leaf):
        if len(self.data) > self.max_data:
            return self.split(leaf)
        else:
            return None

    def split(self,leaf):
        left_data = BTreeNode(
            leaf=leaf,
            arr=self.data[:2],
            children=self.children[:3] if self.children else []
        )
        right_data = BTreeNode(
            leaf=leaf,
            arr=self.data[3:],
            children=self.children[3:] if self.children else []
        )
        separator = self.data[2]
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

class NodePointer(valuePointer):
    def store_child_pointers(self, storage):
        """Persist child objects for a node pointer that still has RAM data."""
        if self.memory_object:
            self.memory_object.store_children(storage)

    @staticmethod
    def bytes_to_ram_object(byte_string):
        """Deserialize a stored node record back into a BinaryNode."""
        data = pickle.loads(byte_string)
        return BTreeNode(
            key=data['key'],
            rightPointer=NodePointer(address=data['rightPointer']),
            leftPointer=NodePointer(address=data['leftPointer']),
            valuePointer=valuePointer(address=data['valuePointer'])
        )

    @staticmethod
    def ram_object_to_bytes(object_string):
        """Serialize a BinaryNode into a pickle record of key and addresses."""
        return pickle.dumps({
            'key':object_string.key,
            'valuePointer':object_string.valuePointer._address,
            'rightPointer': object_string.rightPointer._address,
            'leftPointer':object_string.leftPointer._address
        })

class BTree(logical):
    node_pointer = NodePointer

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

    def update(self,node,key,valuePointer):
        """Insert or replace a key by returning a new node pointer path."""
        if node is None:
            new_node = BTreeNode(
                key,
                valuePointer,
                self.node_pointer(),
                self.node_pointer()
            )
        elif key < node.key:
            new_node = BTreeNode.copy_node(
                node=node,
                leftPointer=self.update(
                    self.traverse(node.leftPointer),
                    key,
                    valuePointer
                )
            )
        elif node.key < key:
            new_node = BTreeNode.copy_node(
                node=node,
                rightPointer=self.update(
                    self.traverse(node.rightPointer),
                    key,
                    valuePointer
                )
            )
        else:
            new_node = BTreeNode.copy_node(
                node=node,
                valuePointer=valuePointer
            )
        return self.node_pointer(memory_object=new_node)

    def remove(self,node,key):
        """Delete a key and return the replacement subtree pointer."""
        if node is None:
            raise KeyError(key)

        if key < node.key:
            return self.node_pointer(
                memory_object=BTreeNode.copy_node(
                    node=node,
                    leftPointer=self.remove(
                        self.traverse(node.leftPointer),
                        key
                    )
                )
            )

        if node.key < key:
            return self.node_pointer(
                memory_object=BTreeNode.copy_node(
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
                memory_object=BTreeNode.copy_node(
                    node=successor,
                    leftPointer=node.leftPointer,
                    rightPointer=new_right
                )
            )
        
        if left is None:
            return node.rightPointer
        
        if right is None:
            return node.leftPointer


    def pop_min(self,pointer):
        """Remove and return the smallest node from a subtree."""
        node = self.traverse(pointer)
        if node is None:
            raise KeyError("empty subtree")

        if self.traverse(node.leftPointer) is None:
            return node, node.rightPointer

        successor, new_left = self.pop_min(node.leftPointer)
        return successor, self.node_pointer(
            memory_object=BTreeNode.copy_node(
                node=node,
                leftPointer=new_left
            )
        )
