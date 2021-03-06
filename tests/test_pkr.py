from datetime import datetime
from decimal import Decimal as D
from collections import OrderedDict
from pkr_hands import HANDS
from pytest import mark, fixture
import pytz
from pytz import UTC
from handparser import PKRHand


@fixture
def hand_header(request):
    h = PKRHand(request.instance.hand_text, parse=False)
    h.parse_header()
    return h


@fixture
def hand(request):
    return PKRHand(request.instance.hand_text)


class TestHoldemHand:
    hand_text = HANDS['holdem_full']

    @mark.parametrize('attribute, expected_value', [
                    ('game_type', 'CASH'),
                    ('sb', D('0.25')),
                    ('bb', D('0.50')),
                    ('date', UTC.localize(datetime(2013, 10, 5, 1, 15, 45))),
                    ('game', 'HOLDEM'),
                    ('limit', 'NL'),
                    ('ident', '2433297728'),
                    ('last_ident', '2433297369'),
                    ('tournament_ident', None),
                    ('tournament_name', None),
                    ('tournament_level', None),
                    ('table_name', "#52121155 - Rapanui's Leela"),
                    ('buyin', D('50')),
                    ('currency', 'USD'),
                    ('money_type', 'R'),
    ])
    def test_header(self, hand_header, attribute, expected_value):
        assert getattr(hand_header, attribute) == expected_value


    @mark.parametrize('attribute, expected_value', [
                      ('players', OrderedDict([('laxi23', D('51.89')), ('NikosMRF', D('50')),
                                              ('Capricorn', D('33.6')), ('Walkman', D('50')),
                                              ('Empty Seat 5', 0), ('barly123', D('50.35'))])),
                      ('button', 'Capricorn'),
                      ('button_seat', 3),
                      ('max_players', 6),   # maybe imprecise
                      ('hero', 'Walkman'),
                      ('hero_seat', 4),
                      ('hero_hole_cards', ('9s', '6d')),
                      ('preflop_actions', ('laxi23 folds',
                                           'Capricorn calls $0.50',
                                           'Walkman folds',
                                           'barly123 raises to $1.25',
                                           'Capricorn calls $1.25')),
                      ('flop', ('7d', '3c', 'Jd')),
                      ('flop_pot', D('2.75')),
                      ('flop_actions', ('barly123 checks',
                                        'Capricorn bets $1.37',
                                        'barly123 raises to $4.11',
                                        'Capricorn calls $4.11')),
                      ('turn', 'Js'),
                      ('turn_pot', D('10.97')),
                      ('turn_actions', ('barly123 checks', 'Capricorn checks')),
                      ('river', '5h'),
                      ('river_pot', D('10.97')),
                      ('river_actions', ('barly123 checks', 'Capricorn checks')),
                      ('total_pot', D('10.97')),
                      ('rake', D('0.54')),
                      ('winners', ('barly123',)),
                      ('show_down', True),
                      ('board', ('7d', '3c', 'Jd', 'Js', '5h'))
                      ])
    def test_body(self, hand, attribute, expected_value):
        assert getattr(hand, attribute) == expected_value
