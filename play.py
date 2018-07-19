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

class Card:

    WIDTH=40
    HEIGHT=10

    def __init__(self, color, shape, number, shading):
        self.color = color
        self.shape = shape
        self.number = number
        self.shading = shading
        self.win = None
        self.shapewins = []

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
        self.win.bkgd(self.color)
        self.win.addstr(0,0,self.text, self.color)
        self.win.refresh()

    def undraw(self, *bkgd_args):
        if self.win is None:
            return
        self.win.clear()
        self.win.bkgd(*bkgd_args)
        self.win.refresh()

class Board:

    BG = BGCOL
    FG = FGCOL
    CARD_BG = FGCOL

    OFFSET_X = 10
    OFFSET_Y = 5

    N_COLS = 3
    N_ROWS = 4

    ROW_WIDTH = 47
    ROW_HEIGHT = 12

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
        self.bkgd = self.init_color(self.FG, self.BG)

        self.card_colors = { k : self.init_color(v, self.CARD_BG, curses.A_BOLD)
                for k, v in self.COLORS.items()}

        self.all_params = list(itertools.product(
                self.card_colors.values(),
                self.SHAPES.values(),
                [1,2,3],
                self.SHADINGS.values()
                ))

        pass

    def init_color(self, fg, bg, attr=0):
        self._col_i += 1
        curses.init_pair(self._col_i, fg, bg)
        return curses.color_pair(self._col_i) | attr

    def run(self):
        self.stdscr.bkgd('-', self.bkgd)
        self.stdscr.refresh()
        self.draw_cards()
        time.sleep(10)

    def draw_cards(self):

        card_params = random.sample(self.all_params, self.N_COLS * self.N_ROWS)

        for i, params in enumerate(card_params):
            x_i = i % self.N_COLS
            y_i = i  / self.N_COLS

            log((x_i, y_i))
            c = Card(*params)
            c.draw((y_i * (self.ROW_HEIGHT)) + self.OFFSET_Y,
                    x_i * self.ROW_WIDTH + self.OFFSET_X)
            time.sleep(.1)

class Game:
    pass


def run(stdscr):
    board = Board(stdscr)
    board.run()


if __name__ == '__main__':
    curses.wrapper(run) 
