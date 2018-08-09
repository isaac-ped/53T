from model import Card, Deck
from logger import *
import itertools
import time

def is_set(a, b, c):
    if a.third(b) == c:
        log("Cards are a set!")
        return True
    else:
        log("Cards are not a set: needed %s, gave %s", a.third(b), c)
        return False

class Game:

    BOARD_SHAPE = (3, 4)

    MAX_CARDS = 18
    MAX_NORMAL = BOARD_SHAPE[0] * BOARD_SHAPE[1]

    DELAY=.1

    def __init__(self, session):
        self.deck = Deck()
        self.deck.shuffle()
        self.layout = dict()
        self.selected = dict()

        self.session = session
        self.scores = { client.id : 0 for client in self.session.clients }
        self.current_yeller = None

    @classmethod
    def iterxy(cls):
        for y in range(cls.BOARD_SHAPE[1]):
            for x in range(cls.BOARD_SHAPE[0]):
                yield x,y
        for ex_x in range(3):
            yield cls.BOARD_SHAPE[0], ex_x
        for ex_x in range(3):
            yield cls.BOARD_SHAPE[0] + 1, ex_x

    def yell_set(self, client):
        if self.current_yeller is None:
            self.session.yell_set(client)
            self.current_yeller = client
        elif self.current_yeller != client:
            self.session.too_late(client)

    def cards_remain(self):
        return self.deck.cards_remaining() > 0

    def next_spot(self):
        for x, y in self.iterxy():
            if self.card_at(x, y) is None:
                return x, y
        return None, None

    def card_at(self, x, y):
        return self.layout.get((x,y), None)

    def valid_card(self, card, x, y):
        card_at = self.card_at(x, y)
        if not card_at == card:
            log_warn("Card at %d %d is %s, not %s", x, y, card_at, card)
            return False
        return True

    def remove_card(self, card, x, y):
        if not self.valid_card(card, x, y):
            log_warn("Cannot remove card")
            return

        self.session.remove_card(card, x, y)
        if (x, y) in self.selected:
            del self.selected[(x, y)]
        del self.layout[(x,y)]

    def select_card(self, card, x, y):
        if not self.valid_card(card, x, y):
            log_warn("Cannot select card")
            return
        self.session.select_card(card, x, y)
        self.selected[(x,y)] = card

    def check_set(self, client):
        if len(self.selected) == 3 and is_set(*self.selected.values()):
            self.scores[client.id] += 1
            self.session.send_scores(self.scores)
            for (x,y), card in self.selected.items():
                self.remove_card(card, x, y)
            self.selected.clear()
            self.fill_board()
            self.reorganize()
        else:
            log("%d cards selected : not a set", len(self.selected))
            self.scores[client.id] -= 1
            self.session.send_scores(self.scores)
            self.selected.clear()
        self.current_yeller = None
        self.session.resume_play()

    def place_three(self):
        for _ in range(3):
            self.place_next()

    def deselect_card(self, card, x, y):
        if not self.valid_card(card, x, y):
            log_warn("Cannot deselect card")
            return
        if not (x,y) in self.selected:
            log_warn("Deselecting non-selected card")
        else:
            del self.selected[(x,y)]
        self.session.deselect_card(card, x, y)

    def place_card(self, card):
        if len(self.layout) == self.MAX_CARDS:
            log_warn("Attempted to place more than MAX_CARDS")
            return
        x, y = self.next_spot()
        if x is None:
            log_error("MAX_CARDS not placed but no next_spot available")
            return
        self.layout[(x,y)] = card
        self.session.place_card(card, x, y)
        #time.sleep(self.DELAY)

    def place_next(self):
        if len(self.layout) == self.MAX_CARDS:
            log_warn("Cannot place more than %d cards", self.MAX_CARDS)
            return
        card = self.deck.draw()
        self.place_card(card)

    def fill_board(self):
        while self.cards_remain() and len(self.layout) < self.MAX_NORMAL:
            self.place_next()

    def iloc(self, i):
        for idx, (x,y) in enumerate(self.iterxy()):
            if idx == i:
                return x, y, self.card_at(x,y)

    def reorganize(self):
        for i in range(self.MAX_CARDS)[::-1]:
            if i < self.MAX_NORMAL:
                return
            x, y, c = self.iloc(i)
            if c is None:
                continue
            else:
                log("Reorganizing card %d", i)
                self.remove_card(c, x, y)
                self.place_card(c)
                updated = True
