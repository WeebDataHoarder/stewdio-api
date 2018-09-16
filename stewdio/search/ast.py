#!/usr/bin/env python3

from psycopg2.sql import Literal, SQL


class Ops:
    ILIKE = 'ILIKE'
    IN = 'IN'
    IN_LOWERCASE = 'IN_LOWERCASE'
    EQUALS = 'EQUALS'
    GREATER_THAN = 'GREATER_THAN'
    LESS_THAN = 'LESS_THAN'


OP_MAP = {
    'ILIKE': lambda k, v: k + SQL(" ILIKE '%' || ") + v + SQL(" || '%'"),
    'IN': lambda k, v: SQL("ARRAY[") + v + SQL("] <@ ") + k,
    'IN_LOWERCASE': lambda k, v: SQL("ARRAY[lower(") + v + SQL(")] <@ ") + k,
    'EQUALS': lambda k, v: k + SQL(" ILIKE ") + v,
    'GREATER_THAN': lambda k, v: k + SQL(" > ") + v,
    'LESS_THAN': lambda k, v: k + SQL(" < ") + v,
}


class OpsConfig:
    def __init__(self, field, supported_ops, default_op):
        self.field = field
        self.supported_ops = supported_ops
        self.default_op = default_op


QUALIFIERS = {
    'title': OpsConfig(SQL('songs.title'), {':': Ops.ILIKE, '=': Ops.EQUALS}, Ops.ILIKE),
    'artist': OpsConfig(SQL('artists.name'), {':': Ops.ILIKE, '=': Ops.EQUALS}, Ops.ILIKE),
    'album': OpsConfig(SQL('albums.name'), {':': Ops.ILIKE, '=': Ops.EQUALS}, Ops.ILIKE),
    'hash': OpsConfig(SQL('songs.hash'), {':': Ops.ILIKE, '=': Ops.EQUALS}, Ops.ILIKE),
    'path': OpsConfig(SQL('songs.path'), {':': Ops.ILIKE, '=': Ops.EQUALS}, Ops.ILIKE),
    'duration': OpsConfig(SQL('songs.duration'), {'>': Ops.GREATER_THAN, '<': Ops.LESS_THAN}, None),
    'fav': OpsConfig(SQL('array_agg(users.name)'), {':': Ops.IN_LOWERCASE,}, Ops.IN_LOWERCASE),
    'tag': OpsConfig(SQL('array_agg(tags.name)'), {':': Ops.IN,}, Ops.IN),
}

# when no qualifier is given, look at all those; must have a default op
UNQUALIFIERS = ('title', 'artist', 'tag')

QUICK = {
    '#': 'tag',
    '/': 'album',
    '@': 'fav',
}


class String:
    def __init__(self, value):
        self.value = value

    def build(self):
        return Literal(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.value == self.value)


class Not:
    def __init__(self, query):
        self.query = query

    def build(self):
        return SQL('NOT ') + self.query.build()

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
        return SQL('(') + self.left.build() + SQL(' AND ') + self.right.build() + SQL(')')

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
        return SQL('(') + self.left.build() + SQL(' OR ') + self.right.build() + SQL(')')

    def __repr__(self):
        return f'{self.__class__.__name__}({self.left!r}, {self.right!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.left == self.left
                and other.right == self.right)


class Qualified:
    def __init__(self, qualifier, search_term, op=None):
        assert qualifier in QUALIFIERS
        self.qualifier = qualifier
        self.search_term = search_term
        self.oc = QUALIFIERS[self.qualifier]
        self.op = op if op else self.oc.default_op

    def build(self):
        return OP_MAP[self.op](self.oc.field, self.search_term.build())

    def __repr__(self):
        op = f', op=Ops.{self.op}' if self.op else ''
        return f'{self.__class__.__name__}({self.qualifier!r}, {self.search_term!r}{op})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.qualifier == self.qualifier
                and other.search_term == self.search_term
                and other.op == self.op)


class Unqualified:
    def __init__(self, search_term):
        self.search_term = search_term

    def build(self):
        def build_one(qualifier):
            oc = QUALIFIERS[qualifier]
            op = oc.default_op
            return OP_MAP[op](oc.field, self.search_term.build())
        return SQL('(') + SQL(' OR ').join(build_one(q) for q in UNQUALIFIERS) + SQL(')')

    def __repr__(self):
        return f'{self.__class__.__name__}({self.search_term!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.search_term == self.search_term)
