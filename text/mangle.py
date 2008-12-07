# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import itertools

import djvu.sexpr
import djvu.const

from text.levenshtein import distance

def mangle(s, t, input):
    s = s.decode('UTF-8', 'replace')
    t = t.decode('UTF-8', 'replace')
    if len(input) == 1 and isinstance(input[0], djvu.sexpr.StringExpression):
        yield t
        return
    input = tuple(map(lambda o: o.value, item) for item in input)
    j = 0
    current_word = ''
    for item in input:
        item[5] = item[5].decode('UTF-8', 'replace')
    for item in input:
        item[5] = len(item[5])
    input_iter = iter(input)
    input_head = input_iter.next()
    for i, ot, to in distance(s, t):
        while i > j:
            if s[j] == ' ':
                yield input_head[:5] + [current_word]
                input_head = input_iter.next()
                current_word = ''
            else:
                current_word += s[j]
            j += 1
        if to == ' ':
            new_len = len(current_word)
            old_len = input_head[5]
            if new_len >= old_len:
                old_len = new_len * 2
            old_width = 0.0 + input_head[3] - input_head[1]
            spc_width = old_width / old_len
            new_width = old_width / old_len * new_len
            yield input_head[:3] + [int(input_head[1] + new_width), input_head[4], current_word]
            input_head[1] += int(new_width + spc_width)
            input_head[5] = old_len
            current_word = ''
        elif ot == ' ':
            current_word += to
            next_head = input_iter.next()
            input_head[2] = min(next_head[2], input_head[2])
            input_head[3] = max(next_head[3], input_head[3])
            input_head[4] = next_head[4]
            input_head[5] = input_head[5] + next_head[5] + len(to)
        else:
            current_word += to
        j = j + len(ot)
    len_s = len(s)
    while j < len_s:
        if s[j] == ' ':
            yield input_head[:5] + [current_word]
            input_head = input_iter.next()
            current_word = ''
        else:
            current_word += s[j]
        j += 1
    yield input_head[:5] + [current_word]

def linearlize_for_export(expr):
    if expr[0].value == djvu.const.TEXT_ZONE_CHARACTER:
        raise CharacterZoneFound
    if len(expr) == 6 and isinstance(expr[5], djvu.sexpr.StringExpression):
        yield expr[5].value
    elif expr[0].value == djvu.const.TEXT_ZONE_LINE:
        yield ' '.join(linearlize_for_export(expr[5:]))
    else:
        for subexpr in expr:
            if not isinstance(subexpr, djvu.sexpr.ListExpression):
                continue
            for item in linearlize_for_export(subexpr):
                yield item

def linearlize_for_import(expr):
    if expr[0].value == djvu.const.TEXT_ZONE_CHARACTER:
        raise CharacterZoneFound
    if expr[0].value == djvu.const.TEXT_ZONE_LINE:
        yield expr
    else:
        for subexpr in expr:
            if not isinstance(subexpr, djvu.sexpr.ListExpression):
                continue
            for item in linearlize_for_import(subexpr):
                yield item

def export(sexpr, stream):
    for line in linearlize_for_export(sexpr):
        print >>stream, line

def import_(sexpr, stdin):
    exported = tuple(linearlize_for_export(sexpr))
    inputs = tuple(linearlize_for_import(sexpr))
    stdin = tuple(line for line in stdin)
    if len(exported) != len(stdin):
        raise LengthChanged
    dirty = False
    for n, line, xline, input in itertools.izip(itertools.count(1), stdin, exported, inputs):
        line = line.rstrip('\n')
        if line != xline:
            input[5:] = list(mangle(xline, line, input[5:]))
            dirty = True
    if not dirty:
        raise NothingChanged
    return sexpr

class NothingChanged(Exception):
    pass

class LengthChanged(Exception):
    pass

class CharacterZoneFound(Exception):
    pass

__all__ = \
(
    'import_', 'export',
    'NothingChanged', 'CharacterZoneFound', 'LengthChanged'
)

# vim:ts=4 sw=4 et
