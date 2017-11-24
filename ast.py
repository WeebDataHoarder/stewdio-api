#!/usr/bin/env python3


class Ops:
    ILIKE = lambda k, v: f"{k} ILIKE '%' || {v} || '%'"
    IN = lambda k, v: f"ARRAY[{v}] <@ {k}"
    EQUALS = lambda k, v: f"{k} ILIKE {v}"


class OpsConfig:
    def __init__(self, field, supported_ops):
        self.field = field
        self.supported_ops = supported_ops


QUALIFIERS = {
    'title': OpsConfig('songs.title', (Ops.ILIKE, Ops.EQUALS)),
    'artist': OpsConfig('artists.name', (Ops.ILIKE, Ops.EQUALS)),
    'album': OpsConfig('albums.name', (Ops.ILIKE, Ops.EQUALS)),
    'path': OpsConfig('songs.location', (Ops.ILIKE, Ops.EQUALS)),
    'fav': OpsConfig('array_agg(users.nick)', (Ops.IN,)),
    'tag': OpsConfig('array_agg(tags.name)', (Ops.IN,)),
}

# when no qualifier is given, look at all those
UNQUALIFIERS = ('title', 'artist', 'tag')


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
    def __init__(self, qualifier, search_term, op=None):
        self.qualifier = qualifier
        self.search_term = search_term
        self.op = op

    def build(self):
        oc = QUALIFIERS[self.qualifier]
        op = self.op or oc.supported_ops[0]
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
        return '(' + ' OR '.join(build_one(q) for q in UNQUALIFIERS) + ')'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.search_term!r})'

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and other.search_term == self.search_term)
