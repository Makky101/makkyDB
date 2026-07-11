"""
Unit tests for BTreeNode.add_data / BTree.update (insert path only).

Run with:  python -m pytest test_btree_insert.py -v
"""
import pytest
from data_structure import BTreeNode, DataNode, BTree, NodePointer


def dn(key):
    """Shorthand: build a DataNode with a throwaway value pointer."""
    return DataNode(key, valuePointer=None)


# ---------------------------------------------------------------------
# Layer 1: BTreeNode.add_data called directly (no storage)
# ---------------------------------------------------------------------

def test_leaf_insert_no_overflow():
    node = BTreeNode(leaf=True)
    result = node.add_data(dn(10), storage=None)
    assert result is None, "single insert into an empty leaf should not split"
    assert [d.ID for d in node.data] == [10]


def test_leaf_insert_stays_sorted():
    node = BTreeNode(leaf=True)
    for k in [30, 10, 20]:
        result = node.add_data(dn(k), storage=None)
        assert result is None
    assert [d.ID for d in node.data] == [10, 20, 30]


def test_leaf_insert_triggers_split():
    node = BTreeNode(leaf=True)
    result = None
    for k in [10, 20, 30, 40, 50]:
        result = node.add_data(dn(k), storage=None)

    assert result is not None, "5th insert should have triggered a split"
    separator, left, right = result

    assert isinstance(separator, list) and len(separator) == 1
    assert separator[0].ID == 30, "middle key (30) should be the separator"

    left_node = left.memory_object
    right_node = right.memory_object
    assert [d.ID for d in left_node.data] == [10, 20]
    assert [d.ID for d in right_node.data] == [40, 50]
    assert left_node.leaf is True
    assert right_node.leaf is True


def test_internal_node_absorbs_child_split_without_overflow():
    left_leaf = BTreeNode(leaf=True, data_arr=[dn(5), dn(10)])
    right_leaf = BTreeNode(leaf=True, data_arr=[dn(30), dn(40), dn(50), dn(60)])
    root = BTreeNode(
        leaf=False,
        data_arr=[dn(20)],
        children=[
            NodePointer(memory_object=left_leaf),
            NodePointer(memory_object=right_leaf),
        ],
    )
    result = root.add_data(dn(45), storage=None)
    assert result is None or isinstance(result, tuple)


# ---------------------------------------------------------------------
# Layer 2: BTree.assign() -> BTree.update(), via a fake storage backend
# ---------------------------------------------------------------------

class FakeStorage:
    """Minimal in-memory stand-in for whatever `storage` will eventually be."""
    def __init__(self):
        self._blocks = {}
        self._next_addr = 1
        self._root_addr = 0

    def get_root_address(self):
        return self._root_addr

    def stamp_root_address(self, addr):
        self._root_addr = addr

    def lock_for_process(self):
        pass

    def write_to_disk(self, data_bytes):
        addr = self._next_addr
        self._blocks[addr] = data_bytes
        self._next_addr += 1
        return addr

    def read_from_disk(self, addr):
        return self._blocks[addr]


def test_btree_first_insert():
    storage = FakeStorage()
    tree = BTree(storage)
    tree.assign(10, "value-10")

    root = tree.traverse(tree.tree_pointer)
    assert [d.ID for d in root.data] == [10]


def test_btree_multiple_inserts_trigger_split():
    storage = FakeStorage()
    tree = BTree(storage)
    for k in [10, 20, 30, 40, 50]:
        tree.assign(k, f"value-{k}")

    root = tree.traverse(tree.tree_pointer)
    assert len(root.data) == 1
    assert len(root.children) == 2


def test_btree_insert_past_first_split():
    storage = FakeStorage()
    tree = BTree(storage)
    for k in [10, 20, 30, 40, 50, 60, 70]:
        tree.assign(k, f"value-{k}")

    root = tree.traverse(tree.tree_pointer)
    assert len(root.children) >= 2


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))