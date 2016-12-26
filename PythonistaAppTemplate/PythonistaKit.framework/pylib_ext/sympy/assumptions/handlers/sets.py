#\input texinfo

"""
Handlers for predicates related to set membership: integer, rational, etc.
"""
from __future__ import print_function, division

from sympy.assumptions import Q, ask
from sympy.assumptions.handlers import CommonHandler, test_closed_group
from sympy import I, S


class AskIntegerHandler(CommonHandler):
    """
    Handler for Q.integer
    Test that an expression belongs to the field of integer numbers
    """

    @staticmethod
    def _number(expr, assumptions):
        # helper method
        try:
            i = int(expr.round())
            if not (expr - i).equals(0):
                raise TypeError
            return True
        except TypeError:
            return False

    @staticmethod
    def Add(expr, assumptions):
        """
        Integer + Integer       -> Integer
        Integer + !Integer      -> !Integer
        !Integer + !Integer -> ?
        """
        if expr.is_number:
            return AskIntegerHandler._number(expr, assumptions)
        return test_closed_group(expr, assumptions, Q.integer)

    @staticmethod
    def Mul(expr, assumptions):
        """
        Integer*Integer      -> Integer
        Integer*Irrational   -> !Integer
        Odd/Even             -> !Integer
        Integer*Rational     -> ?
        """
        if expr.is_number:
            return AskIntegerHandler._number(expr, assumptions)
        _output = True
        for arg in expr.args:
            if not ask(Q.integer(arg), assumptions):
                if arg.is_Rational:
                    if arg.q == 2:
                        return ask(Q.even(2*expr), assumptions)
                    if ~(arg.q & 1):
                        return None
                elif ask(Q.irrational(arg), assumptions):
                    if _output:
                        _output = False
                    else:
                        return
                else:
                    return
        else:
            return _output

    Pow = Add

    int, Integer = [staticmethod(CommonHandler.AlwaysTrue)]*2

    Pi, Exp1, GoldenRatio, Infinity, NegativeInfinity, ImaginaryUnit = \
        [staticmethod(CommonHandler.AlwaysFalse)]*6

    @staticmethod
    def Rational(expr, assumptions):
        # rationals with denominator one get
        # evaluated to Integers
        return False

    @staticmethod
    def Float(expr, assumptions):
        return int(expr) == expr

    @staticmethod
    def Abs(expr, assumptions):
        return ask(Q.integer(expr.args[0]), assumptions)

    @staticmethod
    def MatrixElement(expr, assumptions):
        return ask(Q.integer_elements(expr.args[0]), assumptions)

    Determinant = Trace = MatrixElement


class AskRationalHandler(CommonHandler):
    """
    Handler for Q.rational
    Test that an expression belongs to the field of rational numbers
    """

    @staticmethod
    def Add(expr, assumptions):
        """
        Rational + Rational     -> Rational
        Rational + !Rational    -> !Rational
        !Rational + !Rational   -> ?
        """
        if expr.is_number:
            if expr.as_real_imag()[1]:
                return False
        return test_closed_group(expr, assumptions, Q.rational)

    Mul = Add

    @staticmethod
    def Pow(expr, assumptions):
        """
        Rational ** Integer      -> Rational
        Irrational ** Rational   -> Irrational
        Rational ** Irrational   -> ?
        """
        if ask(Q.integer(expr.exp), assumptions):
            return ask(Q.rational(expr.base), assumptions)
        elif ask(Q.rational(expr.exp), assumptions):
            if ask(Q.prime(expr.base), assumptions):
                return False

    Rational, Float = \
        [staticmethod(CommonHandler.AlwaysTrue)]*2 # Float is finite-precision

    ImaginaryUnit, Infinity, NegativeInfinity, Pi, Exp1, GoldenRatio = \
        [staticmethod(CommonHandler.AlwaysFalse)]*6

    @staticmethod
    def exp(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return ask(~Q.nonzero(x), assumptions)

    @staticmethod
    def cot(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return False

    @staticmethod
    def log(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return ask(~Q.nonzero(x - 1), assumptions)

    sin, cos, tan, asin, atan = [exp]*5
    acos, acot = log, cot


class AskIrrationalHandler(CommonHandler):

    @staticmethod
    def Basic(expr, assumptions):
        _real = ask(Q.real(expr), assumptions)
        if _real:
            _rational = ask(Q.rational(expr), assumptions)
            if _rational is None:
                return None
            return not _rational
        else:
            return _real


class AskRealHandler(CommonHandler):
    """
    Handler for Q.real
    Test that an expression belongs to the field of real numbers
    """

    @staticmethod
    def _number(expr, assumptions):
        # let as_real_imag() work first since the expression may
        # be simpler to evaluate
        i = expr.as_real_imag()[1].evalf(2)
        if i._prec != 1:
            return not i
        # allow None to be returned if we couldn't show for sure
        # that i was 0

    @staticmethod
    def Add(expr, assumptions):
        """
        Real + Real              -> Real
        Real + (Complex & !Real) -> !Real
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        return test_closed_group(expr, assumptions, Q.real)

    @staticmethod
    def Mul(expr, assumptions):
        """
        Real*Real               -> Real
        Real*Imaginary          -> !Real
        Imaginary*Imaginary     -> Real
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        result = True
        for arg in expr.args:
            if ask(Q.real(arg), assumptions):
                pass
            elif ask(Q.imaginary(arg), assumptions):
                result = result ^ True
            else:
                break
        else:
            return result

    @staticmethod
    def Pow(expr, assumptions):
        """
        Real**Integer         -> Real
        Positive**Real        -> Real
        Real**(Integer/Even)  -> Real if base is nonnegative
        Real**(Integer/Odd)   -> Real
        Real**Imaginary       -> ?
        Imaginary**Real       -> ?
        Real**Real            -> ?
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        if ask(Q.imaginary(expr.base), assumptions):
            if ask(Q.real(expr.exp), assumptions):
                if ask(Q.odd(expr.exp), assumptions):
                    return False
                elif ask(Q.even(expr.exp), assumptions):
                    return True
        elif ask(Q.real(expr.base), assumptions):
            if ask(Q.real(expr.exp), assumptions):
                if expr.exp.is_Rational and \
                   ask(Q.even(expr.exp.q), assumptions):
                    return ask(Q.positive(expr.base), assumptions)
                elif ask(Q.integer(expr.exp), assumptions):
                    return True
                elif ask(Q.positive(expr.base), assumptions):
                    return True
                elif ask(Q.negative(expr.base), assumptions):
                    return False

    Rational, Float, Pi, Exp1, GoldenRatio, Abs, re, im = \
        [staticmethod(CommonHandler.AlwaysTrue)]*8

    ImaginaryUnit, Infinity, NegativeInfinity = \
        [staticmethod(CommonHandler.AlwaysFalse)]*3

    @staticmethod
    def sin(expr, assumptions):
        if ask(Q.real(expr.args[0]), assumptions):
            return True

    cos, exp = [sin]*2

    @staticmethod
    def MatrixElement(expr, assumptions):
        return ask(Q.real_elements(expr.args[0]), assumptions)

    Determinant = Trace = MatrixElement

    @staticmethod
    def log(expr, assumptions):
        if ask(Q.positive(expr.args[0]), assumptions):
            return True


class AskExtendedRealHandler(AskRealHandler):
    """
    Handler for Q.extended_real
    Test that an expression belongs to the field of extended real numbers,
    that is real numbers union {Infinity, -Infinity}
    """

    @staticmethod
    def Add(expr, assumptions):
        return test_closed_group(expr, assumptions, Q.extended_real)

    Mul, Pow = [Add]*2

    Infinity, NegativeInfinity = [staticmethod(CommonHandler.AlwaysTrue)]*2


class AskHermitianHandler(AskRealHandler):
    """
    Handler for Q.hermitian
    Test that an expression belongs to the field of Hermitian operators
    """

    @staticmethod
    def Add(expr, assumptions):
        """
        Hermitian + Hermitian  -> Hermitian
        Hermitian + !Hermitian -> !Hermitian
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        return test_closed_group(expr, assumptions, Q.hermitian)

    @staticmethod
    def Mul(expr, assumptions):
        """
        As long as there is at most only one noncommutative term:
        Hermitian*Hermitian         -> Hermitian
        Hermitian*Antihermitian     -> !Hermitian
        Antihermitian*Antihermitian -> Hermitian
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        nccount = 0
        result = True
        for arg in expr.args:
            if ask(Q.antihermitian(arg), assumptions):
                result = result ^ True
            elif not ask(Q.hermitian(arg), assumptions):
                break
            if ask(~Q.commutative(arg), assumptions):
                nccount += 1
                if nccount > 1:
                    break
        else:
            return result

    @staticmethod
    def Pow(expr, assumptions):
        """
        Hermitian**Integer -> Hermitian
        """
        if expr.is_number:
            return AskRealHandler._number(expr, assumptions)
        if ask(Q.hermitian(expr.base), assumptions):
            if ask(Q.integer(expr.exp), assumptions):
                return True

    @staticmethod
    def sin(expr, assumptions):
        if ask(Q.hermitian(expr.args[0]), assumptions):
            return True

    cos, exp = [sin]*2


class AskComplexHandler(CommonHandler):
    """
    Handler for Q.complex
    Test that an expression belongs to the field of complex numbers
    """

    @staticmethod
    def Add(expr, assumptions):
        return test_closed_group(expr, assumptions, Q.complex)

    Mul, Pow = [Add]*2

    Number, sin, cos, exp, re, im, NumberSymbol, Abs, ImaginaryUnit = \
        [staticmethod(CommonHandler.AlwaysTrue)]*9 # they are all complex functions or expressions

    Infinity, NegativeInfinity = [staticmethod(CommonHandler.AlwaysFalse)]*2

    @staticmethod
    def MatrixElement(expr, assumptions):
        return ask(Q.complex_elements(expr.args[0]), assumptions)

    Determinant = Trace = MatrixElement


class AskImaginaryHandler(CommonHandler):
    """
    Handler for Q.imaginary
    Test that an expression belongs to the field of imaginary numbers,
    that is, numbers in the form x*I, where x is real
    """

    @staticmethod
    def _number(expr, assumptions):
        # helper method
        return not expr.as_real_imag()[0].evalf()

    @staticmethod
    def Add(expr, assumptions):
        """
        Imaginary + Imaginary -> Imaginary
        Imaginary + Complex   -> ?
        Imaginary + Real      -> !Imaginary
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        reals = 0
        for arg in expr.args:
            if ask(Q.imaginary(arg), assumptions):
                pass
            elif ask(Q.real(arg), assumptions):
                reals += 1
            else:
                break
        else:
            if reals == 0:
                return True
            if reals == 1 or (len(expr.args) == reals):
                # two reals could sum 0 thus giving an imaginary
                return False

    @staticmethod
    def Mul(expr, assumptions):
        """
        Real*Imaginary      -> Imaginary
        Imaginary*Imaginary -> Real
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        result = False
        reals = 0
        for arg in expr.args:
            if ask(Q.imaginary(arg), assumptions):
                result = result ^ True
            elif not ask(Q.real(arg), assumptions):
                break
        else:
            if reals == len(expr.args):
                return False
            return result

    @staticmethod
    def Pow(expr, assumptions):
        """
        Imaginary**integer -> Imaginary if integer % 2 == 1
        Imaginary**integer -> real if integer % 2 == 0
        Imaginary**Imaginary    -> ?
        Imaginary**Real         -> ?
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        if ask(Q.imaginary(expr.base), assumptions):
            if ask(Q.real(expr.exp), assumptions):
                if ask(Q.odd(expr.exp), assumptions):
                    return True
                elif ask(Q.even(expr.exp), assumptions):
                    return False
        elif ask(Q.real(expr.base), assumptions):
            if ask(Q.real(expr.exp), assumptions):
                if expr.exp.is_Rational and \
                   ask(Q.even(expr.exp.q), assumptions):
                    return ask(Q.negative(expr.base),assumptions)
                elif ask(Q.integer(expr.exp), assumptions):
                    return False
                elif ask(Q.positive(expr.base), assumptions):
                    return False
                elif ask(Q.negative(expr.base), assumptions):
                    return True

    @staticmethod
    def Number(expr, assumptions):
        return not (expr.as_real_imag()[1] == 0)

    NumberSymbol = Number

    ImaginaryUnit = staticmethod(CommonHandler.AlwaysTrue)


class AskAntiHermitianHandler(AskImaginaryHandler):
    """
    Handler for Q.antihermitian
    Test that an expression belongs to the field of anti-Hermitian operators,
    that is, operators in the form x*I, where x is Hermitian
    """

    @staticmethod
    def Add(expr, assumptions):
        """
        Antihermitian + Antihermitian  -> Antihermitian
        Antihermitian + !Antihermitian -> !Antihermitian
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        return test_closed_group(expr, assumptions, Q.antihermitian)

    @staticmethod
    def Mul(expr, assumptions):
        """
        As long as there is at most only one noncommutative term:
        Hermitian*Hermitian         -> !Antihermitian
        Hermitian*Antihermitian     -> Antihermitian
        Antihermitian*Antihermitian -> !Antihermitian
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        nccount = 0
        result = False
        for arg in expr.args:
            if ask(Q.antihermitian(arg), assumptions):
                result = result ^ True
            elif not ask(Q.hermitian(arg), assumptions):
                break
            if ask(~Q.commutative(arg), assumptions):
                nccount += 1
                if nccount > 1:
                    break
        else:
            return result

    @staticmethod
    def Pow(expr, assumptions):
        """
        Hermitian**Integer  -> !Antihermitian
        Antihermitian**Even -> !Antihermitian
        Antihermitian**Odd  -> Antihermitian
        """
        if expr.is_number:
            return AskImaginaryHandler._number(expr, assumptions)
        if ask(Q.hermitian(expr.base), assumptions):
            if ask(Q.integer(expr.exp), assumptions):
                return False
        elif ask(Q.antihermitian(expr.base), assumptions):
            if ask(Q.even(expr.exp), assumptions):
                return False
            elif ask(Q.odd(expr.exp), assumptions):
                return True


class AskAlgebraicHandler(CommonHandler):
    """Handler for Q.algebraic key. """

    @staticmethod
    def Add(expr, assumptions):
        return test_closed_group(expr, assumptions, Q.algebraic)

    @staticmethod
    def Mul(expr, assumptions):
        return test_closed_group(expr, assumptions, Q.algebraic)

    @staticmethod
    def Pow(expr, assumptions):
        return expr.exp.is_Rational and ask(
            Q.algebraic(expr.base), assumptions)

    @staticmethod
    def Rational(expr, assumptions):
        return expr.q != 0

    Float, GoldenRatio, ImaginaryUnit, AlgebraicNumber = \
        [staticmethod(CommonHandler.AlwaysTrue)]*4

    Infinity, NegativeInfinity, ComplexInfinity, Pi, Exp1 = \
        [staticmethod(CommonHandler.AlwaysFalse)]*5

    @staticmethod
    def exp(expr, assumptions):
        x = expr.args[0]
        if ask(Q.algebraic(x), assumptions):
            return ask(~Q.nonzero(x), assumptions)

    @staticmethod
    def cot(expr, assumptions):
        x = expr.args[0]
        if ask(Q.algebraic(x), assumptions):
            return False

    @staticmethod
    def log(expr, assumptions):
        x = expr.args[0]
        if ask(Q.algebraic(x), assumptions):
            return ask(~Q.nonzero(x - 1), assumptions)

    sin, cos, tan, asin, atan = [exp]*5
    acos, acot = log, cot
