# encoding=UTF-8

# Copyright © 2008-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This file is part of djvusmooth.
#
# djvusmooth is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# djvusmooth is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.

class Operation(object):

    def __init__(self, cost):
        self.cost = cost

    def __cmp__(self, other):
        return cmp(self.cost, other.cost)

    def __repr__(self):
        return '{cls}(cost={cost})'.format(
            cls=type(self).__name__,
            cost=self.cost
        )

    def __add__(self, other):
        return self.cost + other

class Delete(Operation):
    pass
class Insert(Operation):
    pass
class Substitute(Operation):
    pass
class Drop(Operation):
    pass
class Append(Operation):
    pass

def distance(s, t):
    len_s = len(s)
    len_t = len(t)
    d = [[None for j in xrange(len_t + 1)] for i in xrange(len_s + 1)]
    for i in xrange(len_s + 1):
        d[i][0] = Drop(i)
    for j in xrange(len_t + 1):
        d[0][j] = Append(j)
    for i in xrange(1, len_s + 1):
        for j in xrange(1, len_t + 1):
            subst_cost = int(s[i - 1] != t[j - 1])
            d[i][j] = min(
                Delete(d[i - 1][j] + 1),
                Insert(d[i][j - 1] + 1),
                Substitute(d[i - 1][j - 1] + subst_cost)
            )
    i = len_s
    j = len_t
    ops = []
    while True:
        op = d[i][j]
        if isinstance(op, Delete):
            i -= 1
            ops += (i, s[i], ''),
        elif isinstance(op, Insert):
            j -= 1
            ops += (i, '', t[j]),
        elif isinstance(op, Substitute):
            i -= 1
            j -= 1
            if s[i] != t[j]:
                ops += (i, s[i], t[j],),
        elif isinstance(op, Append):
            ops += ((i, '', t[jj]) for jj in xrange(j - 1, -1, -1))
            break
        elif isinstance(op, Drop):
            ops += ((ii, s[ii], '') for ii in xrange(i - 1, -1, -1))
            break
    return reversed(ops)

__all__ = ['distance']

# vim:ts=4 sts=4 sw=4 et
