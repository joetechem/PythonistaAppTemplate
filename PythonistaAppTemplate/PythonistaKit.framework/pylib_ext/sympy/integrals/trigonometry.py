#\input texinfo
# -*- coding: utf-8 -*-

from __future__ import print_function, division

from sympy.core import cacheit, Dummy, Eq, Integer, Rational, S, Wild
from sympy.functions import binomial, sin, cos, tan, sec, csc, cot, Piecewise

# TODO sin(a*x)*cos(b*x) -> sin((a+b)x) + sin((a-b)x) ?

# creating, each time, Wild's and sin/cos/Mul is expensive. Also, our match &
# subs are very slow when not cached, and if we create Wild each time, we
# effectively block caching.
#
# so we cache the pattern


@cacheit
def _pat_sincos(x):
    a = Wild('a', exclude=[x])
    n, m = [Wild(s, exclude=[x], properties=[lambda n: isinstance(n, Integer)])
                for s in 'nm']
    pat = sin(a*x)**n * cos(a*x)**m
    return pat, a, n, m

_u = Dummy('u')


def trigintegrate(f, x, conds='piecewise'):
    """Integrate f = Mul(trig) over x

       >>> from sympy import Symbol, sin, cos, tan, sec, csc, cot
       >>> from sympy.integrals.trigonometry import trigintegrate
       >>> from sympy.abc import x

       >>> trigintegrate(sin(x)*cos(x), x)
       sin(x)**2/2

       >>> trigintegrate(sin(x)**2, x)
       x/2 - sin(x)*cos(x)/2

       >>> trigintegrate(tan(x)*sec(x), x)
       1/cos(x)

       >>> trigintegrate(sin(x)*tan(x), x)
       -log(sin(x) - 1)/2 + log(sin(x) + 1)/2 - sin(x)

       http://en.wikibooks.org/wiki/Calculus/Integration_techniques

    See Also
    ========

    sympy.integrals.integrals.Integral.doit
    sympy.integrals.integrals.Integral
    """
    from sympy.integrals.integrals import integrate
    pat, a, n, m = _pat_sincos(x)

    f = f.rewrite('sincos')
    M = f.match(pat)

    if M is None:
        return

    n, m = M[n], M[m]
    if n is S.Zero and m is S.Zero:
        return x
    zz = x if n is S.Zero else S.Zero

    a = M[a]

    if n.is_odd or m.is_odd:
        u = _u
        n_, m_ = n.is_odd, m.is_odd

        # take smallest n or m -- to choose simplest substitution
        if n_ and m_:
            n_ = n_ and (n < m)  # NB: careful here, one of the
            m_ = m_ and not (n < m)  # conditions *must* be true

        #  n      m       u=C        (n-1)/2    m
        # S(x) * C(x) dx  --> -(1-u^2)       * u  du
        if n_:
            ff = -(1 - u**2)**((n - 1)/2) * u**m
            uu = cos(a*x)

        #  n      m       u=S   n         (m-1)/2
        # S(x) * C(x) dx  -->  u  * (1-u^2)       du
        elif m_:
            ff = u**n * (1 - u**2)**((m - 1)/2)
            uu = sin(a*x)

        fi = integrate(ff, u)  # XXX cyclic deps
        fx = fi.subs(u, uu)
        if conds == 'piecewise':
            return Piecewise((zz, Eq(a, 0)), (fx / a, True))
        return fx / a

    # n & m are both even
    #
    #               2k      2m                         2l       2l
    # we transform S (x) * C (x) into terms with only S (x) or C (x)
    #
    # example:
    #  100     4       100        2    2    100          4         2
    # S (x) * C (x) = S (x) * (1-S (x))  = S (x) * (1 + S (x) - 2*S (x))
    #
    #                  104       102     100
    #               = S (x) - 2*S (x) + S (x)
    #       2k
    # then S   is integrated with recursive formula

    # take largest n or m -- to choose simplest substitution
    n_ = (abs(n) > abs(m))
    m_ = (abs(m) > abs(n))
    res = S.Zero

    if n_:
        #  2k         2 k             i             2i
        # C   = (1 - S )  = sum(i, (-) * B(k, i) * S  )
        if m > 0:
            for i in range(0, m//2 + 1):
                res += ((-1)**i * binomial(m//2, i) *
                        _sin_pow_integrate(n + 2*i, x))

        elif m == 0:
            res = _sin_pow_integrate(n, x)
        else:

            # m < 0 , |n| > |m|
            #  /
            # |
            # |    m       n
            # | cos (x) sin (x) dx =
            # |
            # |
            #/
            #                                      /
            #                                     |
            #   -1        m+1     n-1     n - 1   |     m+2     n-2
            # ________ cos (x) sin (x) + _______  |  cos (x) sin (x) dx
            #                                     |
            #   m + 1                     m + 1   |
            #                                    /

            res = (Rational(-1, m + 1) * cos(x)**(m + 1) * sin(x)**(n - 1) +
                   Rational(n - 1, m + 1) *
                   trigintegrate(cos(x)**(m + 2)*sin(x)**(n - 2), x))

    elif m_:
        #  2k         2 k            i             2i
        # S   = (1 - C ) = sum(i, (-) * B(k, i) * C  )
        if n > 0:

            #      /                            /
            #     |                            |
            #     |    m       n               |    -m         n
            #     | cos (x)*sin (x) dx  or     | cos (x) * sin (x) dx
            #     |                            |
            #    /                            /
            #
            #    |m| > |n| ; m, n >0 ; m, n belong to Z - {0}
            #       n                                         2
            #    sin (x) term is expanded here in terms of cos (x),
            #    and then integrated.
            #

            for i in range(0, n//2 + 1):
                res += ((-1)**i * binomial(n//2, i) *
                        _cos_pow_integrate(m + 2*i, x))

        elif n == 0:

            #   /
            #  |
            #  |  1
            #  | _ _ _
            #  |    m
            #  | cos (x)
            # /
            #

            res = _cos_pow_integrate(m, x)
        else:

            # n < 0 , |m| > |n|
            #  /
            # |
            # |    m       n
            # | cos (x) sin (x) dx =
            # |
            # |
            #/
            #                                      /
            #                                     |
            #    1        m-1     n+1     m - 1   |     m-2     n+2
            #  _______ cos (x) sin (x) + _______  |  cos (x) sin (x) dx
            #                                     |
            #   n + 1                     n + 1   |
            #                                    /

            res = (Rational(1, n + 1) * cos(x)**(m - 1)*sin(x)**(n + 1) +
                   Rational(m - 1, n + 1) *
                   trigintegrate(cos(x)**(m - 2)*sin(x)**(n + 2), x))

    else:
        if m == n:
            ##Substitute sin(2x)/2 for sin(x)cos(x) and then Integrate.
            res = integrate((Rational(1, 2)*sin(2*x))**m, x)
        elif (m == -n):
            if n < 0:
                # Same as the scheme described above.
                # the function argument to integrate in the end will
                # be 1 , this cannot be integrated by trigintegrate.
                # Hence use sympy.integrals.integrate.
                res = (Rational(1, n + 1) * cos(x)**(m - 1) * sin(x)**(n + 1) +
                       Rational(m - 1, n + 1) *
                       integrate(cos(x)**(m - 2) * sin(x)**(n + 2), x))
            else:
                res = (Rational(-1, m + 1) * cos(x)**(m + 1) * sin(x)**(n - 1) +
                       Rational(n - 1, m + 1) *
                       integrate(cos(x)**(m + 2)*sin(x)**(n - 2), x))
    if conds == 'piecewise':
        return Piecewise((zz, Eq(a, 0)), (res.subs(x, a*x) / a, True))
    return res.subs(x, a*x) / a


def _sin_pow_integrate(n, x):
    if n > 0:
        if n == 1:
            #Recursion break
            return -cos(x)

        # n > 0
        #  /                                                 /
        # |                                                 |
        # |    n           -1               n-1     n - 1   |     n-2
        # | sin (x) dx =  ______ cos (x) sin (x) + _______  |  sin (x) dx
        # |                                                 |
        # |                 n                         n     |
        #/                                                 /
        #
        #

        return (Rational(-1, n) * cos(x) * sin(x)**(n - 1) +
                Rational(n - 1, n) * _sin_pow_integrate(n - 2, x))

    if n < 0:
        if n == -1:
            ##Make sure this does not come back here again.
            ##Recursion breaks here or at n==0.
            return trigintegrate(1/sin(x), x)

        # n < 0
        #  /                                                 /
        # |                                                 |
        # |    n            1               n+1     n + 2   |     n+2
        # | sin (x) dx = _______ cos (x) sin (x) + _______  |  sin (x) dx
        # |                                                 |
        # |               n + 1                     n + 1   |
        #/                                                 /
        #

        return (Rational(1, n + 1) * cos(x) * sin(x)**(n + 1) +
                Rational(n + 2, n + 1) * _sin_pow_integrate(n + 2, x))

    else:
        #n == 0
        #Recursion break.
        return x


def _cos_pow_integrate(n, x):
    if n > 0:
        if n == 1:
            #Recursion break.
            return sin(x)

        # n > 0
        #  /                                                 /
        # |                                                 |
        # |    n            1               n-1     n - 1   |     n-2
        # | sin (x) dx =  ______ sin (x) cos (x) + _______  |  cos (x) dx
        # |                                                 |
        # |                 n                         n     |
        #/                                                 /
        #

        return (Rational(1, n) * sin(x) * cos(x)**(n - 1) +
                Rational(n - 1, n) * _cos_pow_integrate(n - 2, x))

    if n < 0:
        if n == -1:
            ##Recursion break
            return trigintegrate(1/cos(x), x)

        # n < 0
        #  /                                                 /
        # |                                                 |
        # |    n            -1              n+1     n + 2   |     n+2
        # | cos (x) dx = _______ sin (x) cos (x) + _______  |  cos (x) dx
        # |                                                 |
        # |               n + 1                     n + 1   |
        #/                                                 /
        #

        return (Rational(-1, n + 1) * sin(x) * cos(x)**(n + 1) +
                Rational(n + 2, n + 1) * _cos_pow_integrate(n + 2, x))
    else:
        # n == 0
        #Recursion Break.
        return x
