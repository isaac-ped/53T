import time
from logger import *
import model
import Queue
import curses
import re
from threading import Thread

INVERT = False

if INVERT:
    BGCOL = curses.COLOR_BLACK
    FGCOL = curses.COLOR_WHITE
else:
    BGCOL = curses.COLOR_WHITE
    FGCOL = curses.COLOR_BLACK

import locale
locale.setlocale(locale.LC_ALL, '')

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

# Later, will attempt to redefine COLOR.YELLOW to be grey
COLOR_GREY = curses.COLOR_YELLOW

def utflen(s):
    try:
        return len(s.decode('utf-8'))
    except Exception:
        return len(s)

def utfljust(s, width):
    if s.count('\n') > 0:
        return '\n'.join(utfljust(line, width) for line in s.split('\n'))
    return s + (' ' * (width - utflen(s)))

def center_lines(s, width):
    lines = []
    for l in s.split('\n'):
        lwidth = utflen(l)
        lpad = ' '*int((width - lwidth) / 2)
        rpad = lpad + ' '*((width - lwidth) % 2)
        lines.append(lpad + l + rpad)
    return '\n'.join(lines)

def concat_lines(blocks):
    s1 = blocks[0]
    for s2 in blocks[1:]:

        # Add extra lines to s1 if necessary
        while s1.count('\n') > s2.count('\n'):
            s2 += '\n'
        # Add extra lines to s2 if necessary
        while s2.count('\n') > s1.count('\n'):
            s2 += '\n'

        width = max(utflen(line) for line in s1.split('\n'))
        justified = utfljust(s1, width)

        s1 = '\n'.join(l1 + l2 for l1, l2 in zip(justified.split('\n'),
                                                 s2.split('\n')))

    width = max(utflen(line) for line in s1.split('\n'))
    return utfljust(s1, width)

class CardDrawing:

    WIDTH = 32
    HEIGHT = 10

    def __init__(self, color, shape, number, shading):
        self.color, self.shape, self.number, self.shading = \
                color, shape, number, shading

        self.win = None

        text = self.shade(shape, shading)
        self.text = center_lines(concat_lines([text] * number), self.WIDTH)

    @staticmethod
    def shade(text, fill):
        if fill.strip() == '':
            return text

        # Fills contents of 'text' bordered by non-whitespace
        return re.sub(r"(?<=[/\\|])[ _]*([ _])[ _]*(?=[/\\|])", 
                lambda x: x.group(0).replace(' ', fill).replace('_', fill),
                text)

    def draw(self, y, x):
        log("Drawing card at %d, %d", y, x)

        if self.win is None:
            self.win = curses.newwin(self.HEIGHT, self.WIDTH + 2, y, x)
        self.win.clear()
        self.win.bkgd(self.color.normal)
        self.win.addstr(0, 0, self.text, self.color.normal)
        self.win.refresh()

    def set_selection(self, is_on):
        if self.win is None:
            log_warn("Cannot select undrawn card")
            return

        if is_on:
            col = self.color.selected
        else:
            col = self.color.normal

        self.win.bkgd(col)
        self.win.addstr(0, 0, self.text, col)
        self.win.refresh()

    def undraw(self, bgchar, bgcol):
        if self.win is None:
            log_warn("Cannot undraw undrawn card")
            return
        self.win.clear()
        self.win.bkgd(bgchar, bgcol)
        self.win.refresh()
        log("Undrawed card!")

    def label(self, label):
        self.win.addstr(self.HEIGHT - 2, self.WIDTH - 1, label)
        self.win.refresh()

    def unlabel(self):
        self.win.addstr(self.HEIGHT - 2, self.WIDTH - 1, ' ')
        self.win.refresh()

class Color:

    _COL_INDEX = 0
    NAMED = dict()

    def __init__(self, fg, bg, attrs = 0,
                 selected_fg = None, selected_bg = None, selected_attrs = 0,
                 name = None):
        self.fg, self.bg, self.attrs, self.sel_fg, self.sel_bg, self.sel_attrs = \
                fg, bg, attrs, selected_fg, selected_bg, selected_attrs

        Color._COL_INDEX += 1
        curses.init_pair(self._COL_INDEX, fg, bg)
        self._color = curses.color_pair(self._COL_INDEX) | attrs

        if selected_bg is None:
            selected_bg = bg
        if selected_fg is None:
            selected_fg = fg

        Color._COL_INDEX += 1
        curses.init_pair(self._COL_INDEX, selected_fg, selected_bg)
        self._sel_color = curses.color_pair(self._COL_INDEX) | selected_attrs

        log("Color index raised to %d", self._COL_INDEX)

        if name is not None:
            Color.NAMED[name] = self._color

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

        self.bgcol = Color(self.FG, self.BG)
        self.msgcol = Color(self.MSGFG, self.MSGBG, name="message")

        self.card_colors = {
                k : Color(v, self.CARD_BG, selected_bg = self.SEL_CARD_BG,
                          attrs = curses.A_BOLD)
                for k, v in self.COLORS.items()
        }

        # (x,y) => CardDrawing()
        self.cards = dict()

        self.msgwin = curses.newwin(3, 75, 1, 2)
        self.msgwin.bkgd(self.msgcol.normal)
        self.msgwin.refresh()

    def init(self):
        self.stdscr.bkgd('-', self.bgcol.normal)
        self.stdscr.refresh()

    def card_drawing_kwargs(self, card):
        return dict(
                color = self.card_colors[card.color],
                shape = self.SHAPES[card.shape],
                shading = self.SHADINGS[card.shading],
                number = card.number
        )

    def select_card(self, x, y):
        if (x, y) not in self.cards:
            log_warn("Cannot select (%d, %d): not a placed card", x, y)
        self.cards[(x, y)].set_selection(True)

    def deselect_card(self, x, y):
        if (x, y) not in self.cards:
            log_warn("Cannot deselect (%d, %d): not a placed card", x, y)
        self.cards[(x, y)].set_selection(False)

    @classmethod
    def card_coords(cls, x, y):
        return (y * cls.ROW_HEIGHT + cls.OFFSET_Y,
                x * cls.ROW_WIDTH + cls.OFFSET_X)

    def draw_card(self, card, x, y):
        # TODO: This try block is... annoying...
        # Changes the "full" shading to "#" if the current one can't be displayed
        try:
            kwargs = self.card_drawing_kwargs(card)
            if (x,y) in self.cards:
                self.cards[(x,y)].undraw('-', self.bgcol.normal)
            drawing = CardDrawing(**kwargs)
            drawing.draw(*self.card_coords(x,y))
            self.cards[(x,y)] = drawing
        except Exception as e:
            log_warn("Encountered exception drawing card: %s", e)
            raise
            if self.SHADINGS['f'] != '#':
                self.SHADINGS['f'] = '#'
                self.draw_card(card, x, y)

    def undraw_card(self, x, y):
        if (x,y) not in self.cards:
            log_warn("Cannot undraw (%d, %d): not a placed card", x, y)
            return
        self.cards[(x, y)].undraw('-', self.bgcol.normal)
        del self.cards[(x,y)]

    def display_message(self, message):
        self.msgwin.clear()
        self.msgwin.bkgd(' ', self.msgcol.normal)
        self.msgwin.addstr(1, 1, message)
        self.msgwin.refresh()

    def label_card(self, x, y, label):
        if (x,y) not in self.cards:
            log_warn("Cannot label (%d, %d) %s: not a placed card", x, y, label)
            return
        self.cards[(x, y)].label(label)

    def unlabel_cards(self):
        for card in self.cards.values():
            card.unlabel()

def key_monitor(stdscr, queue):
    while True:
        ch = stdscr.getch()
        queue.enqueue('keypress', key = chr(ch))


class LocalController:

    KEYS = [
            ['1', '2', '3', '4', '5'],
            ['q', 'w', 'e', 'r', 't'],
            ['a', 's', 'd', 'f', 'g'],
            ['z', 'x', 'c', 'v', 'b'],
        ]


    def __init__(self, board, host, queue):
        self.board = board
        self.host = host
        self.queue = queue
        self.layout = {}

        self.keymap = {}
        self.selected = {}
        self.selecting_set = False

        for y, row in enumerate(self.KEYS):
            for x, key in enumerate(row):
                self.keymap[key] = (x, y)

        self.event_handlers = dict(
                keypress = self.handle_keypress,
                place = self.handle_place,
                self_set_yelled = self.handle_self_set_yelled,
                show_message = self.handle_show_message,
                select = self.handle_select,
                deselect = self.handle_deselect,
                resume = self.resume_play,
                remove = self.handle_remove_card
        )

    def resume_play(self):
        self.selecting_set = False
        for (x,y) in self.selected:
            self.board.deselect_card(x,y)
        self.selected.clear()
        self.board.unlabel_cards()

    def handle_remove_card(self, card, x, y):
        log("Removing card...")
        if (x,y) in self.layout:
            del self.layout[(x,y)]
        if (x,y) in self.selected:
            del self.selected[(x,y)]
        self.board.undraw_card(x,y)

    def handle_select(self, card, x, y):
        self.selected[(x, y)] = card
        self.board.select_card(x, y)

    def handle_deselect(self, card, x, y):
        if (x,y) in self.selected:
            del self.selected[(x, y)]
        self.board.deselect_card(x, y)

    def handle_keypress(self, key):
        self.board.display_message("Key %s pressed!" % key)

        if self.selecting_set:
            if key in self.keymap:
                x, y = self.keymap[key]
                if (x, y) not in self.layout:
                    log_warn("(%d, %d) not in self.layout", x, y)
                    return
                if (x, y) not in self.selected:
                    self.host.select_card(self.layout[(x, y)], x, y)
                else:
                    self.host.deselect_card(self.layout[(x, y)], x, y)
            elif key == ' ':
                self.host.check_set()
        elif key == ' ':
            self.host.yell_set()
        elif key == '\n':
            self.host.request_more()

    def handle_place(self, card, x, y):
        log("Placing card %s at (%d, %d)", card, x, y)
        card = model.Card(*card)
        self.layout[(x,y)] = card
        self.board.draw_card(card, x, y)
        time.sleep(.1)

    def handle_show_message(self, message):
        self.board.display_message(message)

    def handle_self_set_yelled(self):
        self.selecting_set = True
        self.board.display_message("Found a set? Select it then!")
        for y, row in enumerate(self.KEYS):
            for x, key in enumerate(row):
                if (x, y) in self.layout:
                    self.board.label_card(x, y, key.upper())

    def control_loop(self, stdscr):
        keypress_thread = Thread(target=key_monitor,
                                 args=(stdscr, self.queue))
        keypress_thread.start()

        while True:
            msg = self.queue.dequeue()

            if 'type' not in msg:
                log_warn("No 'type' in msg: %s", msg)
                continue

            if msg['type'] in self.event_handlers:
                try:
                    self.event_handlers[msg['type']](**msg['args'])
                except Exception as e:
                    log_warn("Exception %s encountered handling event %s",
                             e, msg)
                    raise
            else:
                log_warn("Received unknown message type: %s", msg['type'])

