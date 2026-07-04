from transaction_manager import valuePointer,logical
import pickle

class BinaryNode:
    def __init__(self,key,valuePointer,leftPointer,rightPointer):
        """Hold one key plus pointers to its value and child nodes."""
        self.valuePointer = valuePointer
        self.rightPointer = rightPointer
        self.leftPointer = leftPointer
        self.key = key

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
        return BinaryNode(
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

class Tree(logical):
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
            new_node = BinaryNode(
                key,
                valuePointer,
                self.node_pointer(),
                self.node_pointer()
            )
        elif key < node.key:
            new_node = BinaryNode.copy_node(
                node=node,
                leftPointer=self.update(
                    self.traverse(node.leftPointer),
                    key,
                    valuePointer
                )
            )
        elif node.key < key:
            new_node = BinaryNode.copy_node(
                node=node,
                rightPointer=self.update(
                    self.traverse(node.rightPointer),
                    key,
                    valuePointer
                )
            )
        else:
            new_node = BinaryNode.copy_node(
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
                memory_object=BinaryNode.copy_node(
                    node=node,
                    leftPointer=self.remove(
                        self.traverse(node.leftPointer),
                        key
                    )
                )
            )

        if node.key < key:
            return self.node_pointer(
                memory_object=BinaryNode.copy_node(
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
                memory_object=BinaryNode.copy_node(
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
            memory_object=BinaryNode.copy_node(
                node=node,
                leftPointer=new_left
            )
        )
