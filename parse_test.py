#!/usr/bin/env python3

from parse import *
import pytest


cases = (
    ('''(artist:mizuki OR artist:水樹) AND NOT fav:minus''', And(Or(Qualified('artist', String('mizuki')), Qualified('artist', String('水樹'))), Not(Qualified('fav', String('minus'))))),
    ('''(artist:詩月カオリ OR (artist:utatsuki AND artist:kaori)) AND artist:kotoko''', And(Or(Qualified('artist', String('詩月カオリ')), And(Qualified('artist', String('utatsuki')), Qualified('artist', String('kaori')))), Qualified('artist', String('kotoko')))),
    ('''album:styx AND NOT title:instr''', And(Qualified('album', String('styx')), Not(Qualified('title', String('instr'))))),
    ('''title:"always in this place" OR title:いつもこの場所で''', Or(Qualified('title', String('always in this place')), Qualified('title', String('いつもこの場所で')))),
    ('''album:barbarossa''', Qualified('album', String('barbarossa'))),
    ('''tag:vocaloid''', Qualified('tag', String('vocaloid'))),
    ('''test''', Unqualified(String('test'))),
    ('''fav:SirCmpwn album:"gurren lagann"''', And(Qualified('fav', String('SirCmpwn')), Qualified('album', String('gurren lagann')))),
    ('''album:H.O.T.D NOT fav:minus''', And(Qualified('album', String('H.O.T.D')), Not(Qualified('fav', String('minus'))))),
    ('''one in a billion''', And(And(And(Unqualified(String('one')), Unqualified(String('in'))), Unqualified(String('a'))), Unqualified(String('billion')))),
    ('''one in a billion may'n''', And(And(And(And(Unqualified(String('one')), Unqualified(String('in'))), Unqualified(String('a'))), Unqualified(String('billion'))), Unqualified(String("may'n")))),
    ('''(artist:mizuki OR artist:水樹) AND NOT fav:minus AND album:'supernal liberty' OR million''', Or(And(And(Or(Qualified('artist', String('mizuki')), Qualified('artist', String('水樹'))), Not(Qualified('fav', String('minus')))), Qualified('album', String('supernal liberty'))), Unqualified(String('million')))),
    ('''world.execute(me)''', (ValueError, "Ran into a Token('RPAREN', ')') where it wasn't expected")),
#    ('''path:"comet lucifer" -inst''', (ValueError, "Ran into a Token('WORD', '-inst') where it wasn't expected")),
)

@pytest.mark.parametrize('input,expected', cases)
def test_parse(input, expected):
    try:
        parsed = parse(input)
    except Exception as e:
        parsed = e.__class__, *e.args
    assert parsed == expected
