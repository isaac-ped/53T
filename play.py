import itertools
import logging
import re
import random
import curses
import time
import locale
import codecs
import sys

INVERT = False

if INVERT:
    BGCOL = curses.COLOR_BLACK
    FGCOL = curses.COLOR_WHITE
else:
    BGCOL = curses.COLOR_WHITE
    FGCOL = curses.COLOR_BLACK

logging.basicConfig(filename='play.log',level=logging.DEBUG)

def log(*args, **kwargs):
    logging.info(*args, **kwargs)

import locale
locale.setlocale(locale.LC_ALL, '')

def reallen(s):
    try:
        return len(s.decode('utf-8'))
    except Exception:
        return len(s)

def ljust_ansi(s, width):
    swidth = reallen(s)
    return s + (' ' * (width - swidth))

def center_block(b, width):
    lines = []
    for l in b.split('\n'):
        swidth = reallen(l)
        lpad = ' '*int((width - swidth) / 2)
        rpad = lpad + ' '*((width - swidth) % 2)
        lines.append(lpad + l + rpad)
    return '\n'.join(lines)

def append_block(args, height=0):
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

        fill = str(fill)
        return re.sub(r"(?<=[/\\|])[ _]*([ _])[ _]*(?=[/\\|])", 
                lambda x: x.group(0).replace(' ', fill).replace('_', fill),
                text)


    def draw(self, y, x):
        log("Drawing at %d, %d", y, x)

        if self.win is None:
            self.win = curses.newwin(self.HEIGHT, self.WIDTH+ 2, y, x)
        self.win.clear()
        self.win.bkgd(self.color.normal)
        log("H: %d, W: %d, y: %d, x: %d, text:\n%s", self.HEIGHT, self.WIDTH, y, x, self.text)
        self.win.addstr(0,0,str(self.text), self.color.normal)
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

    def label(self, label):
        self.win.addstr(self.HEIGHT - 2, self.WIDTH - 1, label)
        self.win.refresh()

    def unlabel(self):
        self.win.addstr(self.HEIGHT - 2, self.WIDTH - 1, ' ')
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

    MSGBG = curses.COLOR_BLACK
    MSGFG = curses.COLOR_CYAN

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._col_i = 1
        self.bgcol = Color(self.FG, self.BG)
        self.msgcol = Color(self.MSGFG, self.MSGBG)

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

        self.msgwin = curses.newwin(3, 75, 1, 2)
        self.msgwin.bkgd(self.msgcol.normal)
        self.msgwin.refresh()

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

    def deselect_card(self, x, y):
        if ((x, y) not in self.cards):
            return
        self.cards[(x, y)].set_selected(False)

    def card_coords(self, x, y):
        return (y * self.ROW_HEIGHT + self.OFFSET_Y,
                x * self.ROW_WIDTH + self.OFFSET_X)

    def draw_card(self, card, x, y):
        try:
            params = self.card_drawing_params(card)
            if ((x, y) in self.cards):
                self.cards[(x, y)].undraw('-', self.bgcol.normal)
            card_drawing = CardDrawing(**params)
            card_drawing.draw(*self.card_coords(x, y))
            self.cards[(x, y)] = card_drawing
        except:
            if self.SHADINGS['f'] != '#':
                self.SHADINGS['f'] = '#'
                self.draw_card(card, x, y)

    def undraw_card(self, x, y):
        if ((x, y) not in self.cards):
            log("ERROR: (%d, %d) not a card!", x, y)
        self.cards[(x, y)].undraw('-', self.bgcol.normal)

    def display_message(self, message):
        self.msgwin.clear()
        self.msgwin.bkgd(' ', self.msgcol.normal)
        self.msgwin.addstr(1, 1, message)
        self.msgwin.refresh()

    def label_card(self, x, y, label):
        if (x,y) in self.cards:
            self.cards[(x,y)].label(label)

    def unlabel_cards(self):
        for card in self.cards.values():
            card.unlabel()

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

    MAX_CARDS = 18
    MAX_NORMAL = BOARD_SHAPE[0] * BOARD_SHAPE[1]

    def __init__(self):
        self.deck = Deck()
        self.layout = dict()
        self.deck.shuffle()
        self.selected = dict()

    def cards_remain(self):
        return self.deck.cards_remaining() > 0

    def is_set(self, a, b, c):
        if a.third(b) == c.properties:
            log("Cards are a set!")
            return True
        else:
            log("%s needed, %s given", a.third(b), c.properties)
            return False

    def set_selected(self):
        return len(self.selected) == 3 and self.is_set(*self.selected.values())

    def card_exists(self, x, y):
        return (x, y) in self.layout

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
            #if self.is_full():
            #    return
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
        for ex_x in range(3):
            yield self.BOARD_SHAPE[0], ex_x
        for ex_x in range(3):
            yield self.BOARD_SHAPE[0] + 1, ex_x

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
        if len(self.layout) == self.MAX_CARDS:
            return
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

    def toggle_selection(self, board, x, y):
        if (x, y) in self.layout:
            if (x, y) in self.selected:
                board.deselect_card(x, y)
                del self.selected[(x, y)]
            else:
                board.select_card(x, y)
                self.selected[(x, y)] = self.layout[(x, y)]

    def remove_cards(self, board, cards):
        for card in cards:
            x, y = self.card_loc(card)
            del self.layout[(x, y)]
            board.undraw_card(x, y)

    def remove_selection(self, board):
        log("Removing cards...")
        self.remove_cards(board, self.selected.values())

    def is_full(self):
        for y in range(self.BOARD_SHAPE[1]):
            for x in range(self.BOARD_SHAPE[0]):
                if (x, y) not in self.layout:
                    return False
        return True

    def deselect_all(self, board):
        for x, y in self.selected.keys():
            self.toggle_selection(board, x, y)



class Controller:

    DELAY = .01

    KEYS = [
            ['1', '2', '3', '4', '5'],
            ['q', 'w', 'e', 'r', 't'],
            ['a', 's', 'd', 'f', 'g'],
            ['z', 'x', 'c', 'v', 'b'],
        ]

    def __init__(self, board, game, stdscr):
        self.board = board
        self.game = game
        self.stdscr = stdscr

        self.keymap = {}

        for y, row in enumerate(self.KEYS):
            for x, key in enumerate(row):
                self.keymap[key] = (x, y)

        self.msg = 'Press SPACEBAR for SET | ENTER for CARDS'

    def fill_board(self):
        while self.game.cards_remain() and not self.game.is_full():
            self.game.place_next(self.board)
            time.sleep(self.DELAY)

    def select_set(self):

        while 1:
            ch = chr(self.stdscr.getch())
            if ch in self.keymap:
                x, y = self.keymap[ch]
                if self.game.card_exists(x, y):
                    self.game.toggle_selection(self.board, x, y)
            if ch == ' ':
                if self.game.set_selected():
                    self.game.remove_selection(self.board)
                    self.game.reorganize(self.board)
                    if not self.game.is_full():
                        for _ in range(3):
                            self.game.place_next(self.board)
                            time.sleep(.1)
                self.game.deselect_all(self.board)
                self.board.unlabel_cards()
                return


    def control_loop(self):

        self.fill_board()

        while self.game.cards_remain():

            self.board.display_message(self.msg)

            ch = self.stdscr.getch()
            if ch == ord('\n'):
                for _ in range(3):
                    self.game.place_next(self.board)
            elif ch != ord(' '):
                self.msg = 'I said SPACEBAR or ENTER!'
                self.board.unlabel_cards()
            else:
                self.msg = 'You found a set? Good for you! Select and press SPACE again...'
                self.board.display_message(self.msg)
                for y, row in enumerate(self.KEYS):
                    for x, key in enumerate(row):
                        if self.game.card_exists(x,y):
                            self.board.label_card(x, y, key.upper())
                self.select_set()
                self.msg = 'Press SPACEBAR for SET | ENTER for more CARDS'


def run_controller(stdscr):

    Color.init()
    board = Board(stdscr)
    board.init()
    game = Game()

    Controller(board, game, stdscr).control_loop()

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

        ch = stdscr.getch()
        board.display_message("Pressed: {}".format(chr(ch)))


        while set is not None:
            game.select_cards(board, set)
            time.sleep(.21)
            game.remove_cards(board, set)
            game.reorganize(board)
            set = game.find_set()
        time.sleep(.25)

    time.sleep(2)


if __name__ == '__main__':
    curses.wrapper(run_controller)
