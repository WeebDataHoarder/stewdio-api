#!/usr/bin/env python3

from rply import ParserGenerator, LexerGenerator
from .ast import *

"""
EBNF:

query = ( combination | inverted_query | subquery | elemental_query ) ;

elemental_query = ( qualified | unqualified ) ;
qualified = WORD , ( COLON | EQUALS ) , string ;
unqualified = string ;

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
lg.add('WORD', r'[^:"\'()\s=-][^:)\s=]*')
lg.add('STRING', r'"[^"]*"|\'[^\']*\'')
lg.add('MINUS', r'-')
lg.add('LPAREN', r'\(')
lg.add('RPAREN', r'\)')
lg.add('COLON', r':')
lg.add('EQUALS', r'=')

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
    return String(s)


@pg.production('qualified : WORD COLON string')
@pg.production('qualified : WORD EQUALS string')
def qualified(p):
    assert p[0].value in QUALIFIERS
    op = None
    if p[1].name == 'EQUALS':
        op = Ops.EQUALS
        assert op in QUALIFIERS[p[0].value].supported_ops
    return Qualified(p[0].value, p[2], op)


@pg.production('unqualified : string')
def unqualified(p):
    return Unqualified(p[0])


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
    import psycopg2
    conn = psycopg2.connect('')
    print(ast.build().as_string(conn))
