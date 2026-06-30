import sys
from connector import connect

OK = 0
BAD_ARGS = 1
BAD_VERBS = 2
BAD_KEY = 3

def usage():
    print("Usage:", file=sys.stderr)
    print("\tpython tool.py DBNAME get KEY", file=sys.stderr)
    print("\tpython tool.py DBNAME set KEY VALUE", file=sys.stderr)
    print("\tpython tool.py DBNAME delete KEY", file=sys.stderr)

def main(args):
    if not (4 <= len(args) <= 5):
        usage()
        return BAD_ARGS
    
    concat = args[1:] + [None]

    dbName , cmd , key , value = concat[:4]
    if cmd not in {'get','set','delete'}:
        usage()
        return BAD_VERBS
    
    db_kit = connect.plug(dbName)
    try:
        if cmd == 'get':
            sys.stdout.write(db_kit[key])
        elif cmd == 'set':
            db_kit[key] = value
            db_kit.commit()
        elif cmd == 'delete':
            del db_kit[key]
            db_kit.commit()
    except KeyError:
        print('key not found', file=sys.stderr)
        return BAD_ARGS
    return OK

if __name__ == '__main__':
    sys.exit(main(sys.argv))