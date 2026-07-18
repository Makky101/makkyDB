INTEGER_FORMATS = {
    '8b':"Q",
    '2b': "H",
    '4b':"I"
}
INTEGER_LENGTHS = {
    'NUMBER_LENGTH': 4,
    'TEXT_LENGTH': 2,
    'LONGTEXT': 4,
    'NODE_LENGTH': 8
}
L = '4b' 
D = '2b'
B = '8b'

print('>'+INTEGER_FORMATS[L]+INTEGER_FORMATS[D]+INTEGER_FORMATS[B])