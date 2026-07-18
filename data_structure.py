from transaction_manager import valuePointer,logical
from operator import attrgetter
import pickle


# a small class that holds just the key and the valuepointer
class DataNode:
    def __init__(self,id_num,valuePointer):
        """
        Initialize a data node with an identifier and its associated value pointer.
        
        Parameters:
        	id_num: The node's identifier.
        	valuePointer: The pointer to the associated value.
        """
        self.ID = id_num
        self.vp = valuePointer


class NodePointer(valuePointer):
    def store_child_pointers(self, storage):
        """Persist child objects for a node pointer that still has RAM data."""
        if self.memory_object:
            self.memory_object.store_children(storage)

    @staticmethod
    def fetch_ram_object(metadata,data):
        """
        Deserialize stored data into a B-tree node.
        
        Parameters:
            metadata: Metadata to return with the reconstructed node.
            data: Serialized B-tree node data.
        
        Returns:
            tuple: The original metadata and the reconstructed BTreeNode.
        """
        binary_data = pickle.loads(data)
        pickled_data =  BTreeNode(
            data_arr=binary_data['data_arr'],
            children=[NodePointer(address=address_no) for address_no in binary_data['children_addresses']],
            leaf=binary_data['leaf']
        )

        return (metadata,pickled_data)

    @staticmethod
    def ingest_ram_object(meta_data,object_string):
        """
        Serialize a B-tree node into a metadata and pickle payload tuple.
        
        Parameters:
            meta_data: Metadata associated with the node.
            object_string: B-tree node whose data, child addresses, and leaf status are serialized.
        
        Returns:
            A tuple containing the metadata and serialized node data.
        """
        object_data =  pickle.dumps({
            'data_arr':object_string.data,
            'children_addresses': [node_pointer._address for node_pointer in object_string.children],
            'leaf':object_string.leaf
        })

        payload = (meta_data,object_data)
        return payload

class BTreeNode:
    degree = 5
    max_data = degree - 1
    min_data = (max_data) / 2
    node_pointer = NodePointer
    
    
    def __init__(self,leaf=False,data_arr=None,children=None):
        """
        Initialize a B-tree node with data entries and child pointers.
        
        Parameters:
            leaf (bool): Whether the node is a leaf when child pointers are provided.
            data_arr (list, optional): Initial data entries for the node.
            children (list, optional): Child pointers for the node.
        """
        self.data = data_arr if data_arr else  []
        self.leaf = True if  not children else leaf
        self.children = children if children else []

    def add_data(self,data_node,storage):
        # we have reached the bottom
        """
        Insert a data node into the appropriate position in the B-tree.
        
        Parameters:
        	data_node (DataNode): The data node to insert.
        	storage: Storage used to retrieve child nodes.
        
        Returns:
        	tuple or None: A split result containing the separator and child pointers when the node exceeds its capacity; otherwise, `None`.
        """
        if self.leaf:
            self.data.append(data_node)
            self.data.sort(key=attrgetter("ID"))
            return self.leak(self.leaf)
        else:
            # recursively go down the root if it is not at the botto
            position = 0
            while position < len(self.data) and data_node.ID > self.data[position].ID:
                position += 1
            result = self.children[position].get_object(storage).add_data(data_node,storage)
            if result is None:
                return None
            
            self.absorb(result,position)

            return self.leak(self.leaf)

    # run when one of the child has separated to absorb the separator and handle children
    def absorb(self,result,position):
        """
        Insert a split result into the node at the specified child position.
        
        Parameters:
        	result (tuple): A separator and the left and right child pointers produced by a split.
        	position (int): The index of the child being replaced.
        """
        separator,left_data,right_data = result
        self.data.insert(position,separator[0])
        self.children[position]=left_data 
        self.children.insert(position+1,right_data)
        
    # decides if we should split or not:
    def leak(self,leaf):
        """
        Split the node when it contains more entries than its configured capacity.
        
        Parameters:
        	leaf (bool): Whether the node's children are leaf-level pointers.
        
        Returns:
        	tuple or None: The split result when the node exceeds its maximum entry count; otherwise, `None`.
        """
        if len(self.data) > self.max_data:
            return self.split(leaf)
        else:
            return None

    def split(self,leaf):
        """
        Splits the node into two child pointers and a separator entry.
        
        Parameters:
        	leaf (bool): Indicates whether the resulting child nodes are leaf nodes.
        
        Returns:
        	tuple: A separator entry and pointers to the left and right child nodes.
        """
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
        """Persist this node and its child pointers to storage."""
        self.valuePointer.store_object(storage)
        self.rightPointer.store_object(storage)
        self.leftPointer.store_object(storage)

    @classmethod
    def copy_node(cls,node,**kwargs):
        """
        Create a node copy, optionally replacing selected fields.
        
        Parameters:
            node: The node whose fields provide the default values.
            **kwargs: Field values to use instead of those from `node`.
        
        Returns:
            A new node with the specified field replacements.
        """
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
        """
        Searches the tree for a key and retrieves its associated value.
        
        Parameters:
            key: The key to search for.
            node: The node at which to begin the search.
        
        Returns:
            The value associated with the key, or None if the key is not found.
        """
        while node:
            if key < node.key:
                node = self.traverse(node.leftPointer)
            elif node.key < key:
                node = self.traverse(node.rightPointer)
            else:
                return self.traverse(node.valuePointer)
        return None

    def update(self,storage,root=None,data_node=None):
        """
        Insert a data record into the tree and return the resulting root pointer.
        
        Parameters:
            root: The current root node pointer, or `None` to create an initial root.
            data_node: The data record to insert.
        
        Returns:
            A pointer to the resulting root node.
        """
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
        """
        Remove a key from the subtree rooted at ``node``.
        
        Parameters:
            node: Root pointer of the subtree to modify.
            key: Key to remove.
        
        Returns:
            A pointer to the updated replacement subtree, or ``None`` if the
            removed node has no remaining children.
        
        Raises:
            KeyError: If the key is not found.
        """
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

