"""
This module is the solution of the problem defined at problem.txt
It contains a class with parsing and formatting logic
and a main script, that performs files IO and uses the class.
"""


class Formatter(object):

    """
    This class performs parsing and formatting actions on lines if text.

    It has 2 public methods:
    * parse_line() -- gets an input string of text, parses it and stores
    the result in the inner storage;
    * get_lines() -- retrieves formatted lines of text from inner storage.
    Usage is simple: just parse one line or more, and after get a list (may be
    empty) of filled formatted lines.
    Input and output lines length may differ. One input line may be transormed
    into many output lines or one line or none.
    Use get_lines(flush=True) to force building of non finished lines.
    """

    def __init__(self, linesize=80, tabsize=4):
        """
        Instance constructor.

        Formatter instance can be configured during its initialization trough
        optional keywords params:
        * linesize -- integer value, defines maximum of formatted text width
        in symbols (80 by default);
        * tabsize -- integer value, defines tabulation size for first line of
        each paragraph (4 by default).
        """
        if tabsize < 0:
            raise ValueError("Size of tab must be non-zero!")
        if linesize < 0:
            raise ValueError("Size of line must be non-zero!")
        if tabsize >= linesize:
            raise ValueError("Size of line must be more then the size of tab!")

        self._is_new_paragraph = True
        self._linesize = linesize
        self._tabsize = tabsize
        self._tab = " "*tabsize
        self._max_header_length = linesize/2 + 1
        self._draft_line = []
        self._draft_line_size = self._tabsize
        self._ready_lines = []
        self._paragraph_endings = ['.', '!', '?', ':']
        self.utf8_detected = False
        self.non_utf8_detected = False

    def _get_utf8_symbol_length(self, raw_line, cursor):
        """
        Inner method for optimistic utf-8 symbols detecting.

        Arguments are:
        * raw_line -- non-formatted text line that is currently being parsing;
        * cursor -- integer that points to the first byte of the symbol.

        Returns integer value - length in bytes of the curent symbol.
        Also may mark text as utf-8 or non-utf-8 encoded.
        """
        symbol_len = 1
        if not self.non_utf8_detected:
            # The text may be encoded in utf-8
            max_len = min(4, len(raw_line) - cursor)
            symbol_code = ord(raw_line[cursor])
            # first byte min value, first byte max value, symbol length
            utf8_definitions = (
                (0b11000000, 0b11011111, 2),
                (0b11100000, 0b11101111, 3),
                (0b11110000, 0b11110111, 4),
            )
            if symbol_code <= 127:
                # valid utf-8 symbol, but also valid non-utf8
                # text will not be marked
                symbol_len = 1
            else:
                # possibly multibyte utf-8 symbol
                # check all definitions
                for d in utf8_definitions:
                    if d[2] <= max_len and d[0] <= symbol_code <= d[1]:
                        # first byte is valid, and we got symbol length
                        symbol_len = d[2]
                        if not self.utf8_detected:
                            # if text was not previously marked as utf-8
                            # check the rest of the symbol's bytes
                            for i in range(d[2]-1):
                                next_code = ord(raw_line[cursor+i+1])
                                if not 0b10000000 <= next_code <= 0b10111111:
                                    # symol byte is not valid
                                    # mart text as non-utf8
                                    self.non_utf8_detected = True
                                    symbol_len = 1
                                    break
                            if not self.non_utf8_detected:
                                self.utf8_detected = True
                        break

        return symbol_len

    def parse_line(self, raw_line):
        """
        Parses input raw line.

        Method has one positional argument:
        * raw_line - input line to parse.

        During the line parsing it automaticaly detects multibyte utf-8
        symbols, collects words in a list without spaces,
        and at sertain conditions splits and/or builds justified
        or non justified line of text,
        and stores it at the inner storage.
        It stores the words of non-ended text lines between it's calls.
        """
        raw_line_len = len(raw_line)  # in bytes
        raw_line_is_empty = True  # have not found non-space symbol yet
        in_word = False  # current parser state
        cursor = 0  # points to the first byte of current symbol
        word_start = 0  # points to the first byte of the word's first symbol
        word_len = 0  # word length in symbols (not bytes)
        num_of_words = len(self._draft_line)  # use it to reduce calls to len()

        while cursor < raw_line_len:
            symbol = raw_line[cursor]
            if self.non_utf8_detected or symbol < 'x\80':
                symbol_len = 1
            else:
                # detect multibyte utf-8 symbol on the fly
                symbol_len = self._get_utf8_symbol_length(raw_line, cursor)

            if in_word:
                if symbol.isspace():
                    in_word = False
                    word_end = cursor
                    if num_of_words > 1:
                        if ((self._draft_line_size + word_len + num_of_words)
                                > self._linesize):
                            # new word doesn't fit,
                            # build new line with previously cached words
                            self._build_justified_ready_line()
                            self._is_new_paragraph = False
                            self._draft_line = []
                            self._draft_line_size = 0
                            num_of_words = 0

                    elif self._draft_line_size + word_len > self._linesize:
                        # new word doesn't fit to the empty line
                        raise ValueError("Word '%s' is too long!"
                                         % raw_line[word_start:word_end])

                    # add new word to the cache
                    self._draft_line.append(raw_line[word_start:word_end])
                    self._draft_line_size += word_len
                    num_of_words += 1
                else:
                    word_len += 1
            else:
                if not symbol.isspace():
                    raw_line_is_empty = False
                    word_start = cursor
                    word_len = 1
                    in_word = True

            cursor += symbol_len

        if num_of_words > 0:
            if (self._draft_line[-1][-1] in self._paragraph_endings
                    or raw_line_is_empty):
                # force building of a new line if got paragraph ending sign
                # as a last symbol of the last cached word.
                self._flush()

    def _flush(self):
        """
        Inner method to force the building of a new line from cached words.

        Also finishes the current paragraph.
        """
        num_of_words = len(self._draft_line)
        if num_of_words > 0:
            if not self._is_new_paragraph:
                # last line of a paragraph without paragraph ending sign
                self._build_ready_line()
            else:
                # got one line paragraph
                new_line_len = self._draft_line_size
                if num_of_words > 1:
                    new_line_len += num_of_words - 1
                if new_line_len > self._max_header_length:
                    # got header
                    self._build_justified_ready_line()
                else:
                    # got non header
                    self._build_ready_line()

            self._is_new_paragraph = True
            self._draft_line = []
            self._draft_line_size = self._tabsize

    def _build_justified_ready_line(self):
        """Inner method. Builds new justified line of text."""
        num_of_words = len(self._draft_line)
        if num_of_words > 1:
            # calculate how many spaces should be inserted per word boundary
            num_of_spaces = num_of_words - 1
            spaces_left = self._linesize - self._draft_line_size
            spaces = ' ' * (spaces_left/num_of_spaces)  # cache space item
            extra_spaces = spaces + ' '  # cache long space item
            # get position, from where long space items should be inserted
            extra_spaces_after = num_of_spaces - spaces_left % num_of_spaces
            if self._is_new_paragraph:
                new_line = [self._tab]
            else:
                new_line = []
            space_no = 1
            for word in self._draft_line:
                new_line.append(word)
                if space_no < num_of_words:
                    # insert space item only between words
                    if space_no > extra_spaces_after:
                        # insert long space item
                        new_line.append(extra_spaces)
                    else:
                        # insert regular space item
                        new_line.append(spaces)
                space_no += 1
            new_line.append('\n')
            self._ready_lines.append(''.join(new_line))

        elif num_of_words == 1:
            # build new line of one word, no spaces
            if self._is_new_paragraph:
                new_line = [self._tab, self._draft_line[0], '\n']
            else:
                new_line = [self._draft_line[0], '\n']
            self._ready_lines.append(''.join(new_line))

    def _build_ready_line(self):
        """Inner method. Builds new line of text (no justification)."""
        num_of_words = len(self._draft_line)
        if num_of_words > 0:
            if num_of_words > 1:
                inner = ' '.join(self._draft_line)
            else:
                inner = self._draft_line[0]
            if self._is_new_paragraph:
                new_line = [self._tab, inner, '\n']
            else:
                new_line = [inner, '\n']
            self._ready_lines.append(''.join(new_line))

    def get_lines(self, flush=False):
        """
        Get ready formatted lines fron inner storage,

        This method can force building not fifnished line from cached words by:
        * flush -- boolean value, if True - get cached words of unfinished line
        and build new ready line (False by default).
        Use flush=True if there is nothing more to parse (e.g. at the end of
        a text.)

        Return a list of formatted lines (may be empty).
        """
        if flush:
            self._flush()
        new_lines = []
        if self._ready_lines:
            new_lines = self._ready_lines
            self._ready_lines = []
        return new_lines


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="source file name")
    parser.add_argument("dst", help="output file name")
    args = parser.parse_args()

    with open(args.src, 'r') as src:

        with open(args.dst, 'w') as dst:

            formatter = Formatter(80, 4)

            for line in src:
                formatter.parse_line(line)
                out_lines = formatter.get_lines()
                if out_lines:
                    for out_line in out_lines:
                        dst.write(out_line)

            out_lines = formatter.get_lines(flush=True)
            for out_line in out_lines:
                dst.write(out_line)
