#!/usr/bin/env python3

from rply import ParserGenerator, LexerGenerator
from .ast import *
import re

"""
EBNF:

query = ( combination | inverted_query | subquery | elemental_query ) ;

elemental_query = ( qualified | unqualified | quick | variable ) ;
qualified = WORD , OP , string ;
unqualified = string ;
quick = QUICK , string ;
variable = DOLLAR , string ;

combination = query , [ ( AND | OR ) ] , query ;

not = NOT | MINUS ;
inverted_query = NOT , query ;

subquery = LPAREN , query , RPAREN ;

string = ( WORD | STRING ) ;
"""

lg = LexerGenerator()
lg.add('AND', r'AND')
lg.add('OR', r'OR')
lg.add('NOT', r'NOT')
lg.add('WORD', r'[^:"\'()\s=~<>\-#@/$][^:)\s=~<>]*')
lg.add('STRING', r'([\'"])(?:(?!\1|\\).|\\.)*\1')
lg.add('MINUS', r'-')
lg.add('LPAREN', r'\(')
lg.add('RPAREN', r'\)')
lg.add('OP', r'[:=<>~]')
lg.add('QUICK', r'[#@/]')
lg.add('DOLLAR', r'\$')

lg.ignore(r'\s+')

pg = ParserGenerator(
    [rule.name for rule in lg.rules],
    precedence=[
        ('left', ['AND', 'OR']),
        ('left', ['NOT', 'MINUS']),
    ])


@pg.production('main : query')
def main(p):
    return p[0]


@pg.production('query : combination')
@pg.production('query : inverted_query')
@pg.production('query : subquery')
@pg.production('query : elemental_query')
@pg.production('elemental_query : qualified')
@pg.production('elemental_query : unqualified')
@pg.production('elemental_query : quick')
@pg.production('elemental_query : variable')
@pg.production('not : NOT')
@pg.production('not : MINUS')
def alias(p):
    return p[0]


@pg.production('string : WORD')
@pg.production('string : STRING')
def alias(p):
    s = p[0].value
    if p[0].name == 'STRING':
        s = s[1:-1]
    return String(re.sub(r'\\([\\\'"])', '\\1', s))


@pg.production('qualified : WORD OP string')
def qualified(p):
    qualifier = p[0].value
    assert qualifier in QUALIFIERS
    op = QUALIFIERS[qualifier].supported_ops[p[1].value]
    return Qualified(qualifier, p[2], op)


@pg.production('unqualified : string')
def unqualified(p):
    return Unqualified(p[0])


@pg.production('quick : QUICK string')
def quick(p):
    assert p[0].value in QUICK
    qualifier_name = QUICK[p[0].value]
    return Qualified(qualifier_name, p[1])


@pg.production('variable : DOLLAR string')
def variable(p):
    return Variable(p[1].value)


@pg.production('inverted_query : not query', precedence='NOT')
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


def _printing(it):
    for item in it:
        print(item)
        yield item


def parse(q):
    lex = lexer.lex(q)
    # lex = _printing(lex)
    return parser.parse(lex)


if __name__ == '__main__':
    q = """
(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty' OR million AND #op AND duration>10
"""
    tokens = list(lexer.lex(q))
    # for t in tokens:
    #    print(t)
    print(q)
    ast = parser.parse(iter(tokens))
    print(ast)
    import psycopg2

    conn = psycopg2.connect('')
    print(ast.build(None).as_string(conn))
