import random
from logger import *
import itertools

class Card:

    COLORS = ('r','b','g')
    SHAPES = ('s','d','o')
    SHADINGS = ('e','f','s')
    NUMBERS = (1,2,3)

    def __init__(self, color, shape, shading, number):
        self.color, self.shape, self.shading, self.number = \
                color, shape, shading, number

    @property
    def properties(self):
        return str(self.color), str(self.shape), str(self.shading), self.number

    @staticmethod
    def third_prop(props, prop_a, prop_b):
        if prop_a == prop_b:
            return prop_a
        else:
            for c in props:
                if c != prop_a and c != prop_b:
                    return c

    def third(self, second):
        color = self.third_prop(self.COLORS, self.color, second.color)
        shape = self.third_prop(self.SHAPES, self.shape, second.shape)
        shade = self.third_prop(self.SHADINGS, self.shading, second.shading)
        number = self.third_prop(self.NUMBERS, self.number, second.number)

        return Card(color, shape, shade, number)

    def dict(self):
        return dict(
                color = self.color,
                shape = self.shape,
                shading = self.shading,
                number = self.number
        )

    def __eq__(self, other):
        log("Comparing...")
        return self.properties == other.properties

    def __ne__(self, other):
        log("Comparing not...")
        return self.properties != other.properties

    def __str__(self):
        return '< Card: ' + str(self.properties) + " >"
            
    
    def __repr__(self):
        return str(self)
    
class Deck:

    ALL_PARAMS = list(itertools.product(
        Card.COLORS,
        Card.SHAPES,
        Card.SHADINGS,
        Card.NUMBERS
    ))

    def __init__(self):
        self.all_cards = [Card(*p) for p in self.ALL_PARAMS]

        self.deck = self.all_cards[:]
        log("Deck is %s", self.deck)

    def shuffle(self):
        random.shuffle(self.deck)

    def cards_remaining(self):
        return len(self.deck)

    def draw(self):
        #log("Drawing %dth card", len(self.deck))
        return self.deck.pop()

