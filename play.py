import itertools
import logging
import re
import random
import curses
import time
import locale

INVERT = False

if INVERT:
    BGCOL = curses.COLOR_BLACK
    FGCOL = curses.COLOR_WHITE
else:
    BGCOL = curses.COLOR_WHITE
    FGCOL = curses.COLOR_BLACK

logging.basicConfig(filename='example.log',level=logging.DEBUG)

def log(*args, **kwargs):
    logging.info(*args, **kwargs)

locale.setlocale(locale.LC_ALL,"")

def reallen(s):
    return len(s.decode('utf-8'))

def ljust_ansi(s, width):
    swidth = reallen(s)
    return s + (' ' * (width - swidth))

def center_block(b, width):
    lines = []
    for l in b.split('\n'):
        swidth = reallen(l)
        lpad = ' '*((width - swidth) / 2)
        rpad = lpad + ' '*((width - swidth) % 2)
        lines.append(lpad + l + rpad)
    return '\n'.join(lines)

def append_block(args, height=None):
    s1 = args[0]
    for s2 in args[1:]:

        while s1.count('\n')< height:
            s1 = '\n' + s1

        while s2.count('\n')< height:
            s2 = '\n' + s2
        while s1.count('\n') > s2.count('\n'):
            s2 += '\n'
        while s2.count('\n') > s1.count('\n'):
            s1 += '\n'


        lines = s1.split('\n')
        width = max(reallen(line) for line in lines)
        justified = '\n'.join(ljust_ansi(line, width) for line in lines)

        s1 = '\n'.join(l1 + l2 for l1, l2 in zip(justified.split('\n'), s2.split('\n')))

    width = max(reallen(line) for line in s1.split('\n'))
    s1 = '\n'.join(ljust_ansi(line, width) for line in s1.split('\n'))
    return s1

OVALSTR=r'''
   ___
  /   \
 |     |
 |     |
 |     |
 |     |
  \___/'''

SQUIGGLESTR=r'''
   _____
  /    /
 /    /
 \    \
  |    |
 /    /
/____/'''

DIAMONDSTR=r'''
   /\
  /  \
 /    \
|      |
 \    /
  \  /
   \/'''


SHAPEWIDTH=8

COLOR_GREY = curses.COLOR_YELLOW

class CardDrawing:

    WIDTH=32
    HEIGHT=10

    def __init__(self, color, shape, number, shading):
        self.color = color

        self.shape = shape
        self.number = number
        self.shading = shading
        self.win = None

        shape = self.shade(shape, shading)

        self.text = center_block(append_block([shape] * number), self.WIDTH)

    @staticmethod
    def shade(text, fill):
        if fill.strip() == '':
            return text

        return re.sub(r"(?<=[/\\|])[ _]*([ _])[ _]*(?=[/\\|])", 
                lambda x: x.group(0).replace(' ', fill).replace('_', fill),
                text)


    def draw(self, y, x):
        log("Drawing at %d, %d", y, x)

        self.win = curses.newwin(self.HEIGHT, self.WIDTH+ 2, y, x)
        self.win.bkgd(self.color.normal)
        self.win.addstr(0,0,self.text, self.color.normal)
        self.win.refresh()

    def set_selected(self, flag):
        if self.win is None:
            log("Error: Cannot select undrawn card!")
            return

        if flag:
            col = self.color.selected
        else:
            col = self.color.normal

        self.win.bkgd(col)
        self.win.addstr(0,0,self.text, col)
        self.win.refresh()

    def undraw(self, *bkgd_args):
        if self.win is None:
            return
        self.win.clear()
        self.win.bkgd(*bkgd_args)
        self.win.refresh()

class Color:

    _COL_INDEX = 0

    def __init__(self, fg, bg, sel_fg = None, sel_bg = None, attrs = 0, sel_attrs = 0):
        self.fg, self.bg, self.sel_bg, self.attrs, self.sel_attrs = \
                fg, bg, sel_bg, attrs, sel_attrs

        Color._COL_INDEX += 1
        curses.init_pair(self._COL_INDEX, fg, bg)
        self._color = curses.color_pair(self._COL_INDEX) | attrs

        if sel_bg is None:
            sel_bg = bg
        if sel_fg is None:
            sel_fg = fg

        Color._COL_INDEX += 1
        curses.init_pair(self._COL_INDEX, sel_fg, sel_bg)
        self._sel_color = curses.color_pair(self._COL_INDEX) | attrs

        log(self._COL_INDEX)

    @classmethod
    def init(cls):
        curses.init_color(COLOR_GREY, 200, 200, 200)

    @property
    def normal(self):
        return self._color

    @property
    def selected(self):
        return self._sel_color


class Board:

    BG = BGCOL
    FG = FGCOL
    CARD_BG = FGCOL
    SEL_CARD_BG = COLOR_GREY

    OFFSET_X = 10
    OFFSET_Y = 5

    N_COLS = 3
    N_ROWS = 4

    ROW_WIDTH = 35
    ROW_HEIGHT = 11

    COLORS = dict(
            r = curses.COLOR_RED,
            g = curses.COLOR_GREEN,
            b = curses.COLOR_BLUE
    )

    SHAPES = dict(
            o = OVALSTR,
            s = SQUIGGLESTR,
            d = DIAMONDSTR
    )

    SHADINGS = dict(
            e = ' ',
            s = '-',
            f = u'\u2588'.encode('utf-8')
    )

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._col_i = 1
        self.bgcol = Color(self.FG, self.BG)

        self.card_colors = {
                k : Color(v, self.CARD_BG, sel_bg = self.SEL_CARD_BG, attrs=curses.A_BOLD)
                for k, v in self.COLORS.items()
        }

        self.all_params = list(itertools.product(
                self.card_colors.values(),
                self.SHAPES.values(),
                [1,2,3],
                self.SHADINGS.values()
                ))

        self.cards = dict() # (x,y) => CardDrawing()

        pass

    def init_color(self, fg, bg, sbg=None, attr=0):
        self._col_i += 1
        curses.init_pair(self._col_i, fg, bg)
        col_i = self._col_i
        if sbg is not None:
            self._col_i += 1
            curses.init_pair(self._col_i, fg, sbg)
        return curses.color_pair(col_i) | attr

    def init(self):
        self.stdscr.bkgd('-', self.bgcol.normal)
        self.stdscr.refresh()

    def card_drawing_params(self, card):
        return dict(
                color = self.card_colors[card.color],
                shape = self.SHAPES[card.shape],
                shading = self.SHADINGS[card.shading],
                number = card.number
        )

    def select_card(self, x, y):
        if ((x, y) not in self.cards):
            log("ERROR: (%d,%d) not a card!", x, y)
        self.cards[(x,y)].set_selected(True)


    def card_coords(self, x, y):
        return (y * self.ROW_HEIGHT + self.OFFSET_Y,
                x * self.ROW_WIDTH + self.OFFSET_X)

    def draw_card(self, card, x, y):
        params = self.card_drawing_params(card)
        if ((x, y) in self.cards):
            self.cards[(x, y)].undraw('-', self.bgcol.normal)
        card_drawing = CardDrawing(**params)
        card_drawing.draw(*self.card_coords(x, y))
        self.cards[(x, y)] = card_drawing

    def undraw_card(self, x, y):
        if ((x, y) not in self.cards):
            log("ERROR: (%d, %d) not a card!", x, y)
        self.cards[(x, y)].undraw('-', self.bgcol.normal)

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
        return self.color, self.shape, self.shading, self.number

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

        return color, shape, shade, number


class Deck:

    def __init__(self):
        all_params = list(itertools.product(
            ('r','b','g'),
            ('s','d','o'),
            ('e','f','s'),
            (1,2,3)
        ))

        self.all_cards = [Card(*p) for p in all_params]

        self.deck = self.all_cards[:]

    def shuffle(self):
        random.shuffle(self.deck)

    def cards_remaining(self):
        return len(self.deck)

    def draw(self):
        return self.deck.pop()

class Game:

    BOARD_SHAPE = (3, 4)
    EXTRAS_DIM = 0

    MAX_CARDS = 18
    MAX_NORMAL = BOARD_SHAPE[0] * BOARD_SHAPE[1]

    def __init__(self):
        self.deck = Deck()
        self.layout = dict()
        self.deck.shuffle()

    def cards_remain(self):
        return self.deck.cards_remaining() > 0

    def is_set(self, a, b, c):
        return a.third(b) == c.properties

    def card_loc(self, card):
        for k, v in self.layout.items():
            if card == v:
                return k

    def find_set(self):
        for a in self.itercards():
            for b in self.itercards():
                if b == a:
                    continue
                for c in self.itercards():
                    if c == a or c == b:
                        continue
                    if self.is_set(a, b, c):
                        return a, b, c

    def reorganize(self, board):
        for i in range(self.MAX_CARDS)[::-1]:
            if self.is_full():
                return
            if i < self.BOARD_SHAPE[0] * self.BOARD_SHAPE[1]:
                return
            x, y, c = self.iloc(i)
            if c is None:
                continue
            else:
                log("Reorganizing card %d", i)
                time.sleep(.1)
                self.remove_cards(board, [c])
                x, y = self.next_spot()
                self.place(c, x, y, board)


    def itercards(self):
        for i in range(self.MAX_CARDS):
            _, _, c = self.iloc(i)
            if c is not None:
                yield c

    def iterxy(self):
        for y in range(self.BOARD_SHAPE[1]):
            for x in range(self.BOARD_SHAPE[0]):
                yield x,y
        for ex_b in range(2):
            for ex_a in range(self.BOARD_SHAPE[(self.EXTRAS_DIM + 1) % 2]):
                if self.EXTRAS_DIM == 1:
                    x = ex_a
                    y = self.BOARD_SHAPE[1] + ex_b
                else:
                    x = self.BOARD_SHAPE[0] + ex_b
                    y = ex_a

                yield x, y

    def iloc(self, i): # TODO: This is awful
        for idx, (x,y) in enumerate(self.iterxy()):
            if idx == i:
                return x, y, self.layout.get((x,y), None)

    def next_spot(self):
        for x, y in self.iterxy():
            if (x,y) not in self.layout:
                return x, y
        return None, None

    def place(self, card, x, y, board):
        self.layout[(x,y)] = card
        board.draw_card(card, x, y)

    def place_next(self, board):
        card = self.deck.draw()
        x, y = self.next_spot()
        if x is None:
            return
        self.place(card, x, y, board)

    def place_random(self, board):
        params = random.choice(self.all_params)
        card = Card(*params)
        x, y = random.randint(0,2), random.randint(0,3)
        board.draw_card(card, x, y)
        time.sleep(.1)
        board.select_card(x,y)

    def select_cards(self, board, cards):
        for card in cards:
            x, y = self.card_loc(card)
            board.select_card(x, y)

    def remove_cards(self, board, cards):
        for card in cards:
            x, y = self.card_loc(card)
            del self.layout[(x, y)]
            board.undraw_card(x, y)

    def is_full(self):
        for y in range(self.BOARD_SHAPE[1]):
            for x in range(self.BOARD_SHAPE[0]):
                if (x, y) not in self.layout:
                    return False
        return True


def run(stdscr):
    Color.init()
    board = Board(stdscr)
    board.init()

    game = Game()

    set = None
    while game.cards_remain():
        while game.cards_remain() and (set is None or not game.is_full()):
            for _ in range(3):
                game.place_next(board)
                time.sleep(.1)
            set = game.find_set()
        while set is not None:
            game.select_cards(board, set)
            time.sleep(.21)
            game.remove_cards(board, set)
            game.reorganize(board)
            set = game.find_set()
        time.sleep(.25)

    time.sleep(2)


if __name__ == '__main__':
    curses.wrapper(run)
