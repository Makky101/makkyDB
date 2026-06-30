from transaction_manager import valuePointer,logical
import pickle

class BinaryNode:
    pass

class BinaryNodePointer(valuePointer):
    pass

class Tree(logical):
    node_pointer = BinaryNodePointer
    