import time
import traceback
from logger import *
import model
import curses
import re
from threading import Thread
from remote import MsgHandler

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
        self.y, self.x = None, None
        try:
            text = self.shade(shape, shading)
        except Exception as e: # FIXME: o.O
            text = self.shade(shape, '#')

        self.text = center_lines(concat_lines([text] * number), self.WIDTH)

    @staticmethod
    def shade(text, fill):
        if fill.strip() == '':
            return text

        # Fills contents of 'text' bordered by non-whitespace
        return re.sub(r"(?<=[/\\|])[ _]*([ _])[ _]*(?=[/\\|])", 
                lambda x: x.group(0).replace(' ', fill).replace('_', fill),
                text)

    def redraw(self):
        self.undraw('-', 1)
        self.draw(self.y, self.x)


    def draw(self, y, x):
        log("Drawing card at %d, %d", y, x)
        self.y, self.x = y, x
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

    def undraw(self, bgchar, bgcol=None):
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
        stdscr.keypad(True)
        curses.mousemask(1)

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
        self.resize()


    @classmethod
    def resize(self):
        curses.resizeterm((self.N_ROWS)* (self.ROW_HEIGHT + 2),
                          (self.N_COLS + 2) * (self.ROW_WIDTH + 5))

    @classmethod
    def is_resized(self):
        if curses.is_term_resized((self.N_ROWS)* (self.ROW_HEIGHT + 2),
                (self.N_COLS + 2) * (self.ROW_WIDTH + 5)):
            log("WINDOW WAS RESIZED!")
            return True
        return False


    def refresh(self):
        self.resize()
        self.stdscr.refresh()
        self.msgwin.refresh()
        for card in self.cards.values():
            card.redraw()

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

    @classmethod
    def containing_card(cls, x, y):
        for c_x in range(cls.N_COLS + 2):
            for c_y in range(cls.N_ROWS):
                start_y, start_x = cls.card_coords(c_x, c_y)
                if x > start_x and x < start_x + cls.ROW_WIDTH and \
                        y > start_y and y < start_y + cls.ROW_HEIGHT:
                    return c_x, c_y
        return None, None

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

        if Board.is_resized():
            queue.enqueue_msg('resize')
        if ch in (curses.KEY_BACKSPACE, ord('\x7f'), ord('\b'), '\x08'):
            queue.enqueue_msg('quit')
            return
        if ch == curses.KEY_RESIZE:
            queue.enqueue_msg('resize')
        elif ch == curses.KEY_MOUSE:
            _, x, y, _, _ = curses.getmouse()
            queue.enqueue_msg('mousepress', x = x, y = y)
        else:
            try:
                queue.enqueue_msg('keypress', key = chr(ch))
            except:
                queue.enqueue_msg('show_message', message="Don't press things you're not supposed to")

CONTROL_HANDLERS = {}

class LocalController:

    H = MsgHandler()

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
        self.client_id = None

        self.H.bind(self)

        for y, row in enumerate(self.KEYS):
            for x, key in enumerate(row):
                self.keymap[key] = (x, y)

    @H.register('client_id')
    def handle_self_id(self, id):
        self.client_id = id

    @H.register('quit')
    def handle_quit(self):
        log("Exiting...")
        exit(-1)

    @H.register('resize')
    def handle_resize(self):
        self.board.refresh()

    @H.register('score_update')
    def handle_score_update(self, scores):
        msg = []
        for id, score in scores.items():
            if id == self.client_id:
                msg.append(' YOU : {}'.format(score))
            else:
                msg.append(' Player {}: {} '.format(id, score))

        self.board.display_message('||'.join(msg))

    @H.register('resume')
    def resume_play(self):
        self.selecting_set = False
        for (x,y) in self.selected:
            self.board.deselect_card(x,y)
        self.selected.clear()
        self.board.unlabel_cards()

    @H.register('remove')
    def handle_remove_card(self, card, x, y):
        log("Removing card...")
        if (x,y) in self.layout:
            del self.layout[(x,y)]
        if (x,y) in self.selected:
            del self.selected[(x,y)]
        self.board.undraw_card(x,y)

    @H.register('select')
    def handle_select(self, card, x, y):
        self.selected[(x, y)] = card
        self.board.select_card(x, y)

    @H.register('deselect')
    def handle_deselect(self, card, x, y):
        if (x,y) in self.selected:
            del self.selected[(x, y)]
        self.board.deselect_card(x, y)

    @H.register('mousepress')
    def handle_mousepress(self, x, y):

        if self.selecting_set:
            cx, cy = self.board.containing_card(x, y)
            if cx is None:
                return
            if (cx, cy) not in self.layout:
                log_warn("Non-present (%d,%d) card clicked", cx, cy)
                return
            if (cx, cy) not in self.selected:
                self.host.select_card(self.layout[(cx, cy)], cx, cy)
            else:
                self.host.deselect_card(self.layout[(cx, cy)], cx, cy)
        else:
            self.board.display_message("Must call SET with SPACEBAR first")

    @H.register('keypress')
    def handle_keypress(self, key):

        if self.selecting_set:
            if key in self.keymap:
                x, y = self.keymap[key]
                if (x, y) not in self.layout:
                    log_warn("(%d, %d) not in self.layout", x, y)
                    return
                if (x, y) not in self.selected:
                    self.host.select_card(self.layout[(x, y)].properties, x, y)
                else:
                    self.host.deselect_card(self.layout[(x, y)].properties, x, y)
            elif key == ' ':
                self.host.check_set()
        elif key == ' ':
            self.host.yell_set()
        elif key == '\n':
            self.host.request_more()

    @H.register('place')
    def handle_place(self, card, x, y):
        log("Placing card %s at (%d, %d)", card, x, y)
        card = model.Card(*card)
        self.layout[(x,y)] = card
        self.board.draw_card(card, x, y)
        time.sleep(.1)

    @H.register('show_message')
    def handle_show_message(self, message):
        self.board.display_message(message)

    def handle_other_set_yelled(self):
        self.selecting_set = False
        self.board.display_message("Someone else yelled set!")
        self.selected.clear()
        self.board.unlabel_cards()

    def handle_self_set_yelled(self):
        self.selecting_set = True
        self.board.display_message("Found a set? Select it!")
        for y, row in enumerate(self.KEYS):
            for x, key in enumerate(row):
                if (x, y) in self.layout:
                    self.board.label_card(x, y, key.upper())

    @H.register('set_yelled')
    def handle_set_yelled(self, id):
        if id == self.client_id :
            self.handle_self_set_yelled()
        else:
            self.handle_other_set_yelled()

    @H.register('set_stolen')
    def handle_set_stolen(self, id):
        if id == self.client_id:
            self.handle_self_set_yelled()
            self.board.display_message("You STOLE the chance to SET!")
        else:
            self.handle_other_set_yelled()
            self.board.display_message('Player {} stole the SET!'.format(id))

    @H.register('too_late')
    def handle_too_late(self, id, timeout):
        if id == self.client_id:
            self.board.display_message("Too late! (Wait for {} seconds)".format(timeout))
        else:
            self.board.display_message("Player {} tried to SET too EARLY!".format(id))

    @H.register('end_game')
    def handle_end_game(self, scores):
        scores_txt = []
        for client, score in scores.items():
            if client == self.client_id:
                scores_txt.append("YOU: {}", score)
            else:
                scores_txt.append("P{}:{}".format(client, score))
        winner = sorted(scores.items(), key=lambda x: x[1])[-1][1]
        scores_txt = ' | '.join(scores_txt)
        if winner == scores[str(self.client_id)]:
            self.board.display_message(scores_txt + " :: YOU WINN!")
        else:
            self.board.display_message(scores_txt + " :: YOU LOOOOSE.")


    def control_loop(self, stdscr):
        keypress_thread = Thread(target=key_monitor,
                                 args=(stdscr, self.queue))
        keypress_thread.start()
        self.board.display_message("Press SPACE to call set | BACKSPACE to quit")

        while True:
            msg = self.queue.dequeue()
            log("UI Received message %s", msg)
            self.H.handle(msg['type'], msg['args'], msg['kwargs'])
