from model import Card, Deck
from logger import *
import itertools
import time
import copy

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

    SET_TIMEOUT = 5

    SESSION_CALLS = ('remove', 'select', 'deselect', 'place', 'set_yelled', 'score_update',
                     'set_stolen', 'too_late', 'end_game', 'resume', 'more_requested')

    def __init__(self, session):
        self.deck = Deck()
        self.deck.shuffle()
        self.layout = dict()
        self.selected = dict()

        self.requests = {}
        self.session = session
        self.scores = { client.id : 0 for client in self.session.clients }
        self.current_yeller = None
        self.reset_requests()

    def has_set(self):
        for c1, c2, c3 in itertools.combinations(self.layout.values(), 3):
            if c1.third(c2) == c3:
                return True
        return False

    def reset_requests(self):
        for id in self.session.client_ids():
            self.requests[id] = False

    @classmethod
    def iterxy(cls):
        for y in range(cls.BOARD_SHAPE[1]):
            for x in range(cls.BOARD_SHAPE[0]):
                yield x,y
        for ex_x in range(3):
            yield cls.BOARD_SHAPE[0], ex_x
        for ex_x in range(3):
            yield cls.BOARD_SHAPE[0] + 1, ex_x


    def request_more(self, client):
        self.requests[client.id] = True
        num_requested = len([r for r in self.requests.values() if r])
        self.session.more_requested(client.id, num_requested, len(self.requests))
        if all(self.requests.values()):
            self.place_three()
            self.reset_requests()

    def yell_set(self, client):
        if self.current_yeller is None:
            self.session.set_yelled(client.id)
            self.current_yeller = (client, time.time() + self.SET_TIMEOUT)
            self.requests[client.id] = False
        else:
            yeller, timeout = self.current_yeller
            if self.current_yeller != client:
                if time.time() > timeout:
                    self.deselect_all()
                    self.scores[yeller.id] -= 1
                    self.session.score_update(self.scores)
                    self.session.set_stolen(client.id)
                    self.current_yeller = (client, time.time() + self.TIMEOUT)
                    self.requests[client.id] = False
                else:
                    self.session.too_late(client.id, int(timeout - time.time()))

    def deselect_all(self):
        selected = copy.deepcopy(self.selected)
        for (x,y), card in selected.items():
            self.deselect_card(card, x, y)
        self.selected.clear()


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

        self.session.remove(card.properties, x, y)
        if (x, y) in self.selected:
            del self.selected[(x, y)]
        del self.layout[(x,y)]

    def select_card(self, card, x, y):
        if not self.valid_card(card, x, y):
            log_warn("Cannot select card")
            return
        self.session.select(card.properties, x, y)
        self.selected[(x,y)] = card

    def check_set(self, client):
        if len(self.selected) == 3 and is_set(*self.selected.values()):
            self.scores[client.id] += 1
            self.session.score_update(self.scores)
            selected = copy.deepcopy(self.selected)
            for (x,y), card in selected.items():
                self.remove_card(card, x, y)
            self.selected.clear()
            self.fill_board()
            self.reorganize()
            log("{} cards remaining".format(self.deck.cards_remaining()))
            log("Set present? {}".format(self.has_set()))
            if self.deck.cards_remaining() == 0 and not self.has_set():
                self.session.end_game(self.scores)
                return True
        else:
            log("%d cards selected : not a set", len(self.selected))
            self.scores[client.id] -= 1
            self.session.score_update(self.scores)
            self.selected.clear()
        self.current_yeller = None
        self.session.resume()

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
        self.session.deselect(card.properties, x, y)

    def place_card(self, card):
        if len(self.layout) == self.MAX_CARDS:
            log_warn("Attempted to place more than MAX_CARDS")
            return
        x, y = self.next_spot()
        if x is None:
            log_error("MAX_CARDS not placed but no next_spot available")
            return
        self.layout[(x,y)] = card
        self.session.place(card.properties, x, y)
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

    def disconnect(self, client):
        self.session.end_game(self.scores, "Player {} exited early -- ".format(client.id))
        return True
