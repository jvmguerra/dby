import re

from collections import namedtuple # nt
ntAttr = namedtuple("ntAttr", "attr type max_size pos")
ntTable = namedtuple("Attribute", "type max_size pos")
ntField = namedtuple("Field", "type max_size")

text = 'meuBD	 (Aluno)\n\t   Aluno      (name: varchar(80), age: int, birth: varchar(12), id: 	varchar  (' \
       '14))\n\tAluno(Roberto Rodrigues, 21, 05/04/1994, 54a5s4df)\n'

text = re.sub("[ \t\n]", "", text)

print(text)


reTabel =  "(?P<table> \w+)" #pegar o nome da relação
reAttr = "(?P<attr> [0-9a-zA-Z_/\"]+)" # pegar o nome do atributo
reType = "(: (?P<type> [0-9a-zA-Z]+) ( \( (?P<size> [0-9]+) \) )? )?" #pegar o tipo e o tamanho do atributo, caso existam
reRelation = "(\w+ \( [0-9a-zA-Z_/\"]+ (: [0-9a-zA-Z)(]+ )? (, [0-9a-zA-Z_/\"]+ (: [0-9a-zA-Z(]+ \)? )? )* \) )"

regex1 = re.compile( reTabel + "\(" + reAttr + reType, re.VERBOSE)
regex2 = re.compile("," + reAttr + reType, re.VERBOSE)
regexFull = re.compile(reRelation + "+", re.VERBOSE)
regexRel = re.compile(reRelation, re.VERBOSE)

def check_type (type:str, size:int) -> tuple:
    if not type:
        type, size = None, None
    elif type == "int":
        type = "i"
        size = 4
    elif type == "varchar":
        type = "s"

    return type, size


def treat_table(textRel:str) -> bool:
    lAttr = [] # [ ( attr_name, type, size, pos ) ]
    pos = 0

# matches the first part of the relation. E.g: "Relation1(Attribute1[type1(size1)]"
    match1 = regex1.search(textRel)
    tableName = match1.group("table")
    t = match1.group("type")
    s = match1.group("size")
    t, s = check_type(t, s)
    lAttr.append( ntAttr(match1.group("attr"), t, s, pos) )
    textRel = textRel[match1.end():end]

# matches all attributes and its types, excluding the first.
    iterAttr = regex2.finditer(textRel)
    for match2 in iterAttr:
        pos += 1
        t = match2.group("type")
        s = match2.group("size")
        t, s = check_type(t, s)
        lAttr.append( ntAttr(match2.group("attr"), t, s, pos) )

# check if the relation is a table declaration: only provides types and sizes, not values. E.g: "Aluno (name: varchar(80), age: int)"
    if lAttr[0].type:
        dAttr = dict()
        vReg = [None] * len(lAttr)
        regFmt = "="
        for a in lAttr:
            dAttr[a.attr] = ntTable(a.type, a.size, a.pos)
            vReg[a.pos] = ntField(a.type, a.size)
            regFmt += str(a.size) + a.type
        #Table(tableName, dAttr, vReg, regFmt) # cria nova tabela
# otherwise, it's a table insertion providing values. E.g: "Aluno(Roberto Rodrigues, 21)"
    else:
        lAttr = [x.attr for x in lAttr]
        #insert(tableName, lAttr)

    print(lAttr)

def is_valid(text:str) -> bool:
    match = regexFull.fullmatch(text)
    if not match:
        print("NOT")
        return False
    print(match)
    return True

if not is_valid(text):
    exit()
iterRel = regexRel.finditer(text)
for m in iterRel:
    print(m.group())
    start, end = m.span()
    textRel = text[start:end]
    treat_table(textRel)






