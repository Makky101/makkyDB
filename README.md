# makkyDB

makkyDB is a small file-backed key-value database written from scratch in Python. It stores string keys and string values in a single `.mdb` file using a persistent binary search tree.

The project was adapted from the DBDB idea into the current MakkyDB file names and class names.

## Features

- File-backed key-value storage.
- Default database file: `storage.mdb`.
- Persistent binary search tree for lookup, insert, update, and delete.
- Lazy pointer loading: values and nodes are read from disk when their pointers are traversed.
- Length-prefixed binary object storage.
- A fixed 4096-byte metablock at the start of the file stores the latest root address.
- File locking during write operations with `portalocker`.
- Python dictionary-style API for setting, getting, and deleting values.
- Simple command-line interface.

## Requirements

- Python 3
- `portalocker==3.2.0`
- `pywin32==312`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## File Overview

- `connector.py` opens or creates a database file and returns an `API` object.
- `db_parser.py` defines the public `API` class used by Python code and the CLI.
- `data_structure.py` implements the persistent binary search tree with `BinaryNode`, `NodePointer`, and `Tree`.
- `transaction_manager.py` defines pointer behavior, lazy loading, dirty tracking, assignment, deletion, and stamping.
- `storage_engine.py` handles binary reads/writes, integer packing, file locking, and root-address metadata.
- `user_interface.py` provides the CLI.
- `requirements.txt` lists dependencies.
- `storage.mdb` is a generated database file, not source code.

## Python Usage

```python
from connector import connect

db = connect.plug("storage.mdb")

db["name"] = "Makky"
db.stamp()

print(db["name"])

del db["name"]
db.stamp()
```

Important: writes and deletes are kept in memory until you call `stamp()`.

## CLI Usage

The implemented CLI commands are:

```bash
python user_interface.py select KEY
python user_interface.py assign KEY VALUE
python user_interface.py remove KEY
```

Examples:

```bash
python user_interface.py assign name Makky
python user_interface.py select name
python user_interface.py remove name
```

The CLI always opens the default `storage.mdb` file through `connect.plug()`.

Note: the CLI help text currently prints `get`, `set`, and `delete`, but the code actually accepts `select`, `assign`, and `remove`.

## How Data Is Stored

The first 4096 bytes of the database file are reserved as the metablock. The root node address is written at the start of that block.

Every stored object after the metablock is written as:

1. An 8-byte unsigned big-endian integer containing the byte length.
2. The serialized bytes for the object.

String values are encoded as UTF-8. Tree nodes are serialized with `pickle` and store:

- the node key
- the value pointer address
- the left child pointer address
- the right child pointer address

## Write Flow

1. `db[key] = value` calls `Tree.update(...)` through the transaction layer.
2. The tree records a new in-memory pointer path and marks itself dirty.
3. `db.stamp()` stores pending nodes and values to disk.
4. The storage engine writes the new root pointer into the metablock.
5. The dirty flag is cleared.

Deletion follows the same pattern, except `Tree.remove(...)` rebuilds the affected path and uses `pop_min(...)` when deleting a node with two children.

## Current Limitations

- Keys and values are expected to be strings.
- The tree is not balanced, so lookup performance depends on insertion order.
- There is no transaction rollback.
- There is no automated test suite.
- The CLI help text and implemented command names are not aligned yet.
- The CLI cannot choose a database file; it always uses `storage.mdb`.
- The database file format is experimental and may change.
