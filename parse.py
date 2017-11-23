#!/usr/bin/env python3

from rply import ParserGenerator, LexerGenerator
from rply.token import BaseBox
from enum import Enum
import functools

"""
EBNF:

query = ( combination | inverted_query | subquery | elemental_query ) ;

elemental_query = ( qualified | unqualified ) ;
qualified = WORD , COLON , string ;
unqualified = string ;

combination = query , [ ( AND | OR ) ] , query ;

inverted_query = NOT , query ;

subquery = LPAREN , query , RPAREN ;

string = ( WORD | STRING ) ;
"""

class Ops(Enum):
    ILIKE = lambda k, v: f"{k} ILIKE '%' || {v} || '%'"
    IN = lambda k, v: f"ARRAY[{v}] <@ {k}"
    EQUALS = lambda k, v: f"{k} = {v}"

class OpsConfig:
    def __init__(self, field, supported_ops):
        self.field = field
        self.supported_ops = supported_ops


QUALIFIERS = {
    'title': OpsConfig('songs.title', (Ops.ILIKE, Ops.EQUALS)),
    'artist': OpsConfig('artists.name', (Ops.ILIKE, Ops.EQUALS)),
    'album': OpsConfig('albums.name', (Ops.ILIKE, Ops.EQUALS)),
    'fav': OpsConfig('array_agg(users.nick)', (Ops.IN,)),
    'tag': OpsConfig('array_agg(tags.name)', (Ops.IN,)),
}
# when no qualifier is given, look at all those
UNQUALIFIERS = ('title', 'artist', 'tag')

lg = LexerGenerator()
lg.add('AND', r'AND')
lg.add('OR', r'OR')
lg.add('NOT', r'NOT')
lg.add('WORD', r'[^:"\'()\s-][^:)\s]*')
lg.add('STRING', r'"[^"]*"|\'[^\']*\'')
#lg.add('MINUS', r'-')
lg.add('LPAREN', r'\(')
lg.add('RPAREN', r'\)')
lg.add('COLON', r':')

lg.ignore(r'\s+')


pg = ParserGenerator(
        [rule.name for rule in lg.rules],
        precedence=[
            ('left', ['AND', 'OR']),
            ('left', ['NOT']),
            ],
        cache_id='query-lang')

class String:
    def __init__(self, value):
        self.value = value

    def build(self):
        return repr(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.value == self.value)


class Not:
    def __init__(self, query):
        self.query = query

    def build(self):
        return f'NOT {self.query.build()}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.query!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.query == self.query)


class And:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def build(self):
        return f'({self.left.build()} AND {self.right.build()})'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.left!r}, {self.right!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.left == self.left
                and other.right == self.right)


class Or:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def build(self):
        return f'({self.left.build()} OR {self.right.build()})'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.left!r}, {self.right!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.left == self.left
                and other.right == self.right)


class Qualified:
    def __init__(self, qualifier, search_term):
        self.qualifier = qualifier
        self.search_term = search_term

    def build(self):
        oc = QUALIFIERS[self.qualifier]
        op = oc.supported_ops[0]
        return op(oc.field, self.search_term.build())

    def __repr__(self):
        return f'{self.__class__.__name__}({self.qualifier!r}, {self.search_term!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.qualifier == self.qualifier
                and other.search_term == self.search_term)


class Unqualified:
    def __init__(self, search_term):
        self.search_term = search_term

    def build(self):
        def build_one(qualifier):
            oc = QUALIFIERS[qualifier]
            op = oc.supported_ops[0]
            return op(oc.field, self.search_term.build())
        return '(' + ' OR '.join(build_one for q in UNQUALIFIERS) + ')'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.search_term!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.search_term == self.search_term)


@pg.production('main : query')
def main(p):
    # p is a list, of each of the pieces on the right hand side of the
    # grammar rule
    return p[0]


@pg.production('query : combination')
@pg.production('query : inverted_query')
@pg.production('query : subquery')
@pg.production('query : elemental_query')
@pg.production('elemental_query : qualified')
@pg.production('elemental_query : unqualified')
def alias(p):
    return p[0]


@pg.production('string : WORD')
@pg.production('string : STRING')
def alias(p):
    s = p[0].value
    if p[0].name == 'STRING':
        s = s[1:-1]
    return String(s)


@pg.production('qualified : WORD COLON string')
def qualified(p):
    return Qualified(p[0].value, p[2])


@pg.production('unqualified : string')
def unqualified(p):
    return Unqualified(p[0])


@pg.production('inverted_query : NOT query')
def inverted_query(p):
    return Not(p[1])


@pg.production('combination : query AND query')
def combination_and(p):
    return And(p[0], p[2])


@pg.production('combination : query OR query')
def combination_or(p):
    return Or(p[0], p[2])


@pg.production('combination : query query', precedence='AND')
def combination_implicit_and(p):
    return And(p[0], p[1])


@pg.production('subquery : LPAREN query RPAREN')
def subquery(p):
    return p[1]


@pg.error
def error_handler(token):
    raise ValueError(f"Ran into a {token} where it wasn't expected")


lexer = lg.build()
parser = pg.build()


def parse(q):
    return parser.parse(lexer.lex(q))


if __name__ == '__main__':
    q = """
(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty' OR million
"""
    tokens = list(lexer.lex(q))
    #for t in tokens:
    #    print(t)
    print(q)
    ast = parser.parse(iter(tokens))
    print(ast)
    print(ast.build())
