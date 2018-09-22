#!/usr/bin/env python3

from .parse import *
from psycopg2.sql import *
import pytest


cases = (
    ('''(artist:mizuki OR artist:水樹) AND NOT fav:minus''', And(Or(Qualified('artist', String('mizuki')), Qualified('artist', String('水樹'))), Not(Qualified('fav', String('minus')))), None),
    ('''(artist:詩月カオリ OR (artist:utatsuki AND artist:kaori)) AND artist:kotoko''', And(Or(Qualified('artist', String('詩月カオリ')), And(Qualified('artist', String('utatsuki')), Qualified('artist', String('kaori')))), Qualified('artist', String('kotoko'))), None),
    ('''album:styx AND NOT title:instr''', And(Qualified('album', String('styx')), Not(Qualified('title', String('instr')))), None),
    ('''title:"always in this place" OR title:いつもこの場所で''', Or(Qualified('title', String('always in this place')), Qualified('title', String('いつもこの場所で'))), None),
    ('''album:barbarossa''', Qualified('album', String('barbarossa')), None),
    ('''tag:vocaloid''', Qualified('tag', String('vocaloid')), None),
    ('''test''', Unqualified(String('test')), None),
    ('''fav:SirCmpwn album:"gurren lagann"''', And(Qualified('fav', String('SirCmpwn')), Qualified('album', String('gurren lagann'))), None),
    ('''album:H.O.T.D NOT fav:minus''', And(Qualified('album', String('H.O.T.D')), Not(Qualified('fav', String('minus')))), None),
    ('''one in a billion''', And(And(And(Unqualified(String('one')), Unqualified(String('in'))), Unqualified(String('a'))), Unqualified(String('billion'))), None),
    ('''one in a billion may'n''', And(And(And(And(Unqualified(String('one')), Unqualified(String('in'))), Unqualified(String('a'))), Unqualified(String('billion'))), Unqualified(String("may'n"))), None),
    ('''(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty' OR million''', Or(And(And(Or(Qualified('artist', String('mizuki')), Qualified('artist', String('水樹'))), Not(Qualified('fav', String('minus')))), Qualified('album', String('supernal liberty'))), Unqualified(String('million'))), None),
    ('''world.execute(me)''', (ValueError, "Ran into a Token('RPAREN', ')') where it wasn't expected"), None),
    ('''path:"comet lucifer" -inst''', And(Qualified('path', String('comet lucifer')), Not(Unqualified(String('inst')))), None),
    ('''(fav:minus OR fav:nyc OR fav:jdiez) NOT fav:sircmpwn''', And(Or(Or(Qualified('fav', String('minus')), Qualified('fav', String('nyc'))), Qualified('fav', String('jdiez'))), Not(Qualified('fav', String('sircmpwn')))), Composed([SQL('('), SQL('('), SQL('('), SQL('EXISTS('), SQL('SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = '), Composed([SQL('lower('), Literal('minus'), SQL(')')]), SQL(')'), SQL(' OR '), SQL('EXISTS('), SQL('SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = '), Composed([SQL('lower('), Literal('nyc'), SQL(')')]), SQL(')'), SQL(')'), SQL(' OR '), SQL('EXISTS('), SQL('SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = '), Composed([SQL('lower('), Literal('jdiez'), SQL(')')]), SQL(')'), SQL(')'), SQL(' AND '), SQL('NOT '), SQL('EXISTS('), SQL('SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = '), Composed([SQL('lower('), Literal('sircmpwn'), SQL(')')]), SQL(')'), SQL(')')])),
    ('''title="why?"''', Qualified('title', String('why?'), op=Ops.EQUALS), None),
    ('''#op @minus''', And(Qualified('tag', String('op')), Qualified('fav', String('minus'))), None),
    ('''@minus''', Qualified('fav', String('minus')), Composed([SQL('EXISTS('), SQL('SELECT 1 FROM users JOIN favorites ON (favorites.user_id = users.id) WHERE favorites.song = songs.id AND users.name = '), Composed([SQL('lower('), Literal('minus'), SQL(')')]), SQL(')')])),
    ('''duration>10 AND duration<500''', And(Qualified('duration', String('10'), op=Ops.GREATER_THAN), Qualified('duration', String('500'), op=Ops.LESS_THAN)), None),
)

@pytest.mark.parametrize('input,expected_ast,expected_sql', cases)
def test_parse(input, expected_ast, expected_sql):
    try:
        parsed = parse(input)
    except Exception as e:
        parsed = e.__class__, *e.args
    assert expected_ast == parsed
    if expected_sql is not None:
        generated_sql = parsed.build()
        print(generated_sql)
        assert generated_sql == expected_sql
