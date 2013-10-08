import re
from StringIO import StringIO
from datetime import datetime
from decimal import Decimal
from collections import OrderedDict, MutableMapping
import pytz


ET = pytz.timezone('US/Eastern')
POKER_ROOMS = {'PokerStars': 'STARS'}
TYPES = {'Tournament': 'TOUR'}
GAMES = {"Hold'em": 'HOLDEM'}
LIMITS = {'No Limit': 'NL'}


class PokerStarsHand(MutableMapping):
    date_format = '%Y/%m/%d %H:%M:%S'
    _header_pattern = re.compile(r"""
                                (?P<poker_room>^PokerStars)[ ]           # Poker Room
                                Hand[ ]\#(?P<number>\d*):[ ]            # Hand number
                                (?P<game_type>Tournament)[ ]            # Type
                                \#(?P<tournament_ident>\d*),[ ]         # Tournament Number
                                \$(?P<buyin>\d*\.\d{2})\+               # buyin
                                \$(?P<rake>\d*\.\d{2})[ ]               # rake
                                (?P<currency>USD|EUR)[ ]                # currency
                                (?P<game>.*)[ ]                         # game
                                (?P<limit>No[ ]Limit)[ ]                # limit
                                -[ ]Level[ ](?P<tournament_level>.*)[ ] # Level
                                \((?P<sb>.*)/(?P<bb>.*)\)[ ]            # blinds
                                -[ ].*[ ]                               # localized date
                                \[(?P<date>.*)[ ]ET\]$                  # ET date
                                """, re.VERBOSE | re.MULTILINE)
    _table_pattern = re.compile(r"^Table '(.*)' (\d)-max Seat #(\d) is the button$", re.MULTILINE)
    _seat_pattern = re.compile(r"^Seat (\d): (.*) \((\d*) in chips\)$", re.MULTILINE)
    _preflop_pattern = re.compile(r"^Dealt to (\w*) \[(.{2}) (.{2})\](.*?)(?=\*{3})", re.MULTILINE | re.DOTALL)
    _flop_pattern = re.compile(r"^\*\*\* FLOP \*\*\* \[.. .. ..\](.*?)\*\*\*", re.MULTILINE | re.DOTALL)
    _turn_pattern = re.compile(r"^\*\*\* TURN \*\*\* \[.. .. ..\] \[..\](.*?)\*\*\*", re.MULTILINE | re.DOTALL)
    _river_pattern = re.compile(r"^\*\*\* RIVER \*\*\* \[.. .. .. ..\] \[..\](.*?)\*\*\*", re.MULTILINE | re.DOTALL)
    _board_pattern = re.compile(r"^Board \[(.*?)\]$", re.MULTILINE)
    _pot_pattern = re.compile(r"^Total pot (\d*) .*\| Rake (\d*)$", re.MULTILINE)
    _winner_pattern = re.compile(r"^(.*?) collected ", re.MULTILINE)
    _summary_showdown_pattern = re.compile(r"^Seat (\d): (.*) showed .* and won.$", re.MULTILINE)
    _ante_pattern = re.compile(r"posts the ante (\d*)", re.MULTILINE)

    def __init__(self, hand_text, parse=True):
        self.raw = hand_text.strip() + "\n"
        self.header_parsed, self.parsed = False, False

        if parse:
            self.parse()

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        if key != 'raw':
            return getattr(self, key)
        else:
            raise KeyError('You can only get it via the attribute like "hand.raw"')

    def __setitem__(self, key, value):
        self.header_parsed, self.parsed = False, False
        setattr(self, key, value)

    def __delitem__(self, key):
        self.header_parsed, self.parsed = False, False
        delattr(self, key)

    def keys(self):
        return [attr for attr in vars(self) if not attr.startswith('_') and attr != 'raw']

    def __iter__(self):
        return iter(self.keys())

    def parse_header(self):
        """
        Parses the first line of a hand history.
        """
        match = self._header_pattern.search(self.raw)
        self.poker_room = POKER_ROOMS[match.group('poker_room')]
        self.game_type = TYPES[match.group('game_type')]
        self.sb = Decimal(match.group('sb'))
        self.bb = Decimal(match.group('bb'))
        self.buyin = Decimal(match.group('buyin'))
        self.rake = Decimal(match.group('rake'))
        self.date = ET.localize(datetime.strptime(match.group('date'), self.date_format))
        self.game = GAMES[match.group('game')]
        self.limit = LIMITS[match.group('limit')]
        self.number = match.group('number')
        self.tournament_ident = match.group('tournament_ident')
        self.tournament_level = match.group('tournament_level')
        self.currency = match.group('currency')

        self.header_parsed = True

    def parse(self):
        """
        Parse the body of the hand history, but first parse header if not yet parsed.
        """
        if not self.header_parsed:
            self.parse_header()

        self._parse_table()
        self._search_players()
        self._search_ante()
        self._parse_preflop()
        self._parse_street('flop')
        self._parse_street('turn')
        self._parse_street('river')
        self._search_showdown()
        self._search_board()
        self._search_total_pot()
        self._search_winners()

        self.parsed = True

    def _parse_table(self):
        match = self._table_pattern.search(self.raw)
        self.table_name = match.group(1)
        self.max_players = int(match.group(2))
        self.button_seat = int(match.group(3))

    def _search_players(self):
        players = [('Empty Seat %s' % num, 0) for num in range(1, self.max_players + 1)]
        for playerdata in self._seat_pattern.findall(self.raw):
            players[int(playerdata[0]) - 1] = (playerdata[1], int(playerdata[2]))
        self.players = OrderedDict(players)
        self.button = players[self.button_seat - 1][0]

    def _search_ante(self):
        match = self._ante_pattern.search(self.raw)
        self.ante = int(match.group(1)) if match else None

    def _parse_preflop(self):
        match = self._preflop_pattern.search(self.raw)
        self.hero = match.group(1)
        self.hero_hole_cards = match.group(2, 3)
        self.preflop_actions = tuple(match.group(4).strip().splitlines())
        self.hero_seat = self.players.keys().index(self.hero) + 1

    def _parse_street(self, street):
        setattr(self, '%s_actions' % street, None)
        street_pattern = getattr(self, "_%s_pattern" % street)
        match = street_pattern.search(self.raw)
        if match:
            actions = match.group(1).strip()
            actions = tuple(actions.splitlines()) if actions else None
            setattr(self, '%s_actions' % street, actions)

    def _search_showdown(self):
        self.show_down = False
        if "SHOW DOWN" in self.raw:
            self.show_down = True

    def _search_total_pot(self):
        match = self._pot_pattern.search(self.raw)
        self.total_pot = int(match.group(1))

    def _search_board(self):
        self.board = self.flop = self.turn = self.river = None
        match = self._board_pattern.search(self.raw)
        if match:
            cards = match.group(1).split()
            self.board = tuple(cards)
            self.flop = tuple(cards[:3])
            self.turn = cards[3] if len(cards) > 3 else None
            self.river = cards[4] if len(cards) > 4 else None

    def _search_winners(self):
        winners = set()
        match = self._winner_pattern.search(self.raw)
        if match:
            winners.add(match.group(1))
        match = self._summary_showdown_pattern.search(self.raw)
        if match:
            winners.add(match.group(1))
        self.winners = tuple(winners)
