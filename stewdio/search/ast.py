#!/usr/bin/env python3

from psycopg2.sql import Literal, SQL


class Ops:
    ILIKE = 'ILIKE'
    IN_LOOSE_ILIKE = 'IN_LOOSE_ILIKE'
    IN_ILIKE = 'IN_ILIKE'
    IN_EQUALS = 'IN_EQUALS'
    IN_LOWERCASE = 'IN_LOWERCASE'
    EQUALS = 'EQUALS'
    PLAIN_EQUALS = 'PLAIN_EQUALS'
    GREATER_THAN = 'GREATER_THAN'
    LESS_THAN = 'LESS_THAN'
    JSONB_KEY_EXISTS_LOWERCASE = 'JSONB_KEY_EXISTS_LOWERCASE'


OP_MAP = {
    'ILIKE': lambda k, v: k + SQL(" ILIKE '%' || ") + v + SQL(" || '%'"),
    'IN_LOOSE_ILIKE': lambda k, v: k['field'] + SQL(' IN(SELECT ') + k['table_value'] + SQL(' FROM ') + k['table'] + SQL(' WHERE ') + k['table_field'] + SQL(" % ") + v + SQL(' ORDER BY similarity(') + k['table_field'] + SQL(', ') + v + SQL(') DESC, id ASC)'),
    'IN_ILIKE': lambda k, v: k['field'] + SQL(' IN(SELECT ') + k['table_value'] + SQL(' FROM ') + k['table'] + SQL(' WHERE ') + k['table_field'] + SQL(" ILIKE '%' || ") + v + SQL(" || '%'") + SQL(')'),
    'IN_EQUALS': lambda k, v: k['field'] + SQL(' IN(SELECT ') + k['table_value'] + SQL(' FROM ') + k['table'] + SQL(' WHERE ') + k['table_field'] + SQL(" ILIKE ") + v + SQL(')'),
    'IN_LOWERCASE': lambda k, v: SQL('EXISTS(') + k.format(SQL('lower({})').format(v)) + SQL(')'),
    'EQUALS': lambda k, v: k + SQL(' ILIKE ') + v,
    'PLAIN_EQUALS': lambda k, v: k + SQL(' = ') + v,
    'GREATER_THAN': lambda k, v: k + SQL(' > ') + v,
    'LESS_THAN': lambda k, v: k + SQL(' < ') + v,
    'JSONB_KEY_EXISTS_LOWERCASE': lambda k, v: SQL('{}::jsonb').format(k) + SQL(' ? ') + SQL('lower({})').format(v),
}


class OpsConfig:
    def __init__(self, field, supported_ops, default_op):
        self.field = field
        self.supported_ops = supported_ops
        self.default_op = default_op


IN_STRING_OPS = {':': Ops.IN_ILIKE, '=': Ops.IN_EQUALS, '~': Ops.IN_LOOSE_ILIKE}
STRING_OPS = {':': Ops.ILIKE, '=': Ops.EQUALS}
NUM_OPS = {':': Ops.PLAIN_EQUALS, '=': Ops.PLAIN_EQUALS, '>': Ops.GREATER_THAN, '<': Ops.LESS_THAN, }

QUALIFIERS = {
    'title': OpsConfig({'field': SQL('id'), 'table': SQL('songs'), 'table_value': SQL('id'), 'table_field': SQL('title')}, IN_STRING_OPS, Ops.IN_ILIKE),
    'artist': OpsConfig({'field': SQL('artist'), 'table': SQL('artists'), 'table_value': SQL('id'), 'table_field': SQL('name')}, IN_STRING_OPS, Ops.IN_ILIKE),
    'album': OpsConfig({'field': SQL('album'), 'table': SQL('albums'), 'table_value': SQL('id'), 'table_field': SQL('name')}, IN_STRING_OPS, Ops.IN_ILIKE),
    'lyrics': OpsConfig(SQL('songs.lyrics'), {':': Ops.JSONB_KEY_EXISTS_LOWERCASE, '=': Ops.JSONB_KEY_EXISTS_LOWERCASE, }, Ops.JSONB_KEY_EXISTS_LOWERCASE),
    'hash': OpsConfig(SQL('songs.hash'), STRING_OPS, Ops.ILIKE),
    'audio': OpsConfig(SQL('songs.audio_hash'), STRING_OPS, Ops.ILIKE),
    'path': OpsConfig(SQL('songs.path'), STRING_OPS, Ops.ILIKE),
    'duration': OpsConfig(SQL('songs.duration'), NUM_OPS, Ops.PLAIN_EQUALS),
    'fav': OpsConfig(SQL(
        'SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = {}'),
                     {':': Ops.IN_LOWERCASE, '=': Ops.IN_LOWERCASE }, Ops.IN_LOWERCASE),
    'tag': OpsConfig(SQL(
        'SELECT 1 FROM taggings JOIN tags ON (taggings.tag = tags.id) WHERE taggings.song = songs.id AND tags.name = {}'),
                     {':': Ops.IN_LOWERCASE, '=': Ops.IN_LOWERCASE }, Ops.IN_LOWERCASE),

    'favcount': OpsConfig(SQL('songs.favorite_count'), NUM_OPS, Ops.PLAIN_EQUALS),
    'tagcount': OpsConfig(SQL('songs.tag_count'), NUM_OPS, Ops.PLAIN_EQUALS),
    'playcount': OpsConfig(SQL('songs.play_count'), NUM_OPS, Ops.PLAIN_EQUALS),
}

# when no qualifier is given, look at all those; must have a default op
UNQUALIFIERS = ('title', 'artist', 'album', 'tag')

QUICK = {
    '#': 'tag',
    '/': 'album',
    '@': 'fav',
}


class Context:
    # not part of the AST
    def __init__(self, artist=None, album=None, audio=None):
        self.artist = artist
        self.album = album
        self.audio = audio


class String:
    def __init__(self, value):
        self.value = value

    def build(self, context):
        return Literal(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.value == self.value)


class Not:
    def __init__(self, query):
        self.query = query

    def build(self, context):
        return SQL('NOT ') + self.query.build(context)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.query!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.query == self.query)


class And:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def build(self, context):
        return SQL('(') + self.left.build(context) + SQL(' AND ') + self.right.build(context) + SQL(')')

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

    def build(self, context):
        return SQL('(') + self.left.build(context) + SQL(' OR ') + self.right.build(context) + SQL(')')

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

    def build(self, context):
        return OP_MAP[self.op](self.oc.field, self.search_term.build(context))

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

    def build(self, context):
        def build_one(qualifier):
            oc = QUALIFIERS[qualifier]
            op = oc.default_op
            return OP_MAP[op](oc.field, self.search_term.build(context))

        return SQL('(') + SQL(' OR ').join(build_one(q) for q in UNQUALIFIERS) + SQL(')')

    def __repr__(self):
        return f'{self.__class__.__name__}({self.search_term!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.search_term == self.search_term)


class Variable:
    def __init__(self, name):
        self.name = name
        self.oc = QUALIFIERS[name]

    def build(self, context):
        return OP_MAP[self.oc.supported_ops['=']](self.oc.field, Literal(getattr(context, self.name)))

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and other.name == self.name)
