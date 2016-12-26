#\input texinfo

"""Logic for applying operators to states.

Todo:
* Sometimes the final result needs to be expanded, we should do this by hand.
"""

from __future__ import print_function, division

from sympy import Add, Mul, Pow, sympify, S

from sympy.physics.quantum.anticommutator import AntiCommutator
from sympy.physics.quantum.commutator import Commutator
from sympy.physics.quantum.dagger import Dagger
from sympy.physics.quantum.innerproduct import InnerProduct
from sympy.physics.quantum.operator import OuterProduct, Operator
from sympy.physics.quantum.state import State, KetBase, BraBase, Wavefunction
from sympy.physics.quantum.tensorproduct import TensorProduct

__all__ = [
    'qapply'
]


#-----------------------------------------------------------------------------
# Main code
#-----------------------------------------------------------------------------

def qapply(e, **options):
    """Apply operators to states in a quantum expression.

    Parameters
    ==========

    e : Expr
        The expression containing operators and states. This expression tree
        will be walked to find operators acting on states symbolically.
    options : dict
        A dict of key/value pairs that determine how the operator actions
        are carried out.

        The following options are valid:

        * ``dagger``: try to apply Dagger operators to the left
          (default: False).
        * ``ip_doit``: call ``.doit()`` in inner products when they are
          encountered (default: True).

    Returns
    =======

    e : Expr
        The original expression, but with the operators applied to states.
    """
    from sympy.physics.quantum.density import Density

    dagger = options.get('dagger', False)

    if e == 0:
        return S.Zero

    # This may be a bit aggressive but ensures that everything gets expanded
    # to its simplest form before trying to apply operators. This includes
    # things like (A+B+C)*|a> and A*(|a>+|b>) and all Commutators and
    # TensorProducts. The only problem with this is that if we can't apply
    # all the Operators, we have just expanded everything.
    # TODO: don't expand the scalars in front of each Mul.
    e = e.expand(commutator=True, tensorproduct=True)

    # If we just have a raw ket, return it.
    if isinstance(e, KetBase):
        return e

    # We have an Add(a, b, c, ...) and compute
    # Add(qapply(a), qapply(b), ...)
    elif isinstance(e, Add):
        result = 0
        for arg in e.args:
            result += qapply(arg, **options)
        return result

    # For a Density operator call qapply on its state
    elif isinstance(e, Density):
        new_args = [(qapply(state, **options), prob) for (state,
                     prob) in e.args]
        return Density(*new_args)

    # For a raw TensorProduct, call qapply on its args.
    elif isinstance(e, TensorProduct):
        return TensorProduct(*[qapply(t, **options) for t in e.args])

    # For a Pow, call qapply on its base.
    elif isinstance(e, Pow):
        return qapply(e.base, **options)**e.exp

    # We have a Mul where there might be actual operators to apply to kets.
    elif isinstance(e, Mul):
        result = qapply_Mul(e, **options)
        if result == e and dagger:
            return Dagger(qapply_Mul(Dagger(e), **options))
        else:
            return result

    # In all other cases (State, Operator, Pow, Commutator, InnerProduct,
    # OuterProduct) we won't ever have operators to apply to kets.
    else:
        return e


def qapply_Mul(e, **options):

    ip_doit = options.get('ip_doit', True)

    args = list(e.args)

    # If we only have 0 or 1 args, we have nothing to do and return.
    if len(args) <= 1 or not isinstance(e, Mul):
        return e
    rhs = args.pop()
    lhs = args.pop()

    # Make sure we have two non-commutative objects before proceeding.
    if (sympify(rhs).is_commutative and not isinstance(rhs, Wavefunction)) or \
            (sympify(lhs).is_commutative and not isinstance(lhs, Wavefunction)):
        return e

    # For a Pow with an integer exponent, apply one of them and reduce the
    # exponent by one.
    if isinstance(lhs, Pow) and lhs.exp.is_Integer:
        args.append(lhs.base**(lhs.exp - 1))
        lhs = lhs.base

    # Pull OuterProduct apart
    if isinstance(lhs, OuterProduct):
        args.append(lhs.ket)
        lhs = lhs.bra

   # Call .doit() on Commutator/AntiCommutator.
    if isinstance(lhs, (Commutator, AntiCommutator)):
        comm = lhs.doit()
        if isinstance(comm, Add):
            return qapply(
                e.func(*(args + [comm.args[0], rhs])) +
                e.func(*(args + [comm.args[1], rhs])),
                **options
            )
        else:
            return qapply(e.func(*args)*comm*rhs, **options)

    # Apply tensor products of operators to states
    if isinstance(lhs, TensorProduct) and all([isinstance(arg, Operator) or arg == 1 for arg in lhs.args]) and \
            isinstance(rhs, TensorProduct) and all([isinstance(arg, State) or arg == 1 for arg in rhs.args]) and \
            len(lhs.args) == len(rhs.args):
        result = TensorProduct(*[qapply(lhs.args[n]*rhs.args[n], **options) for n in range(len(lhs.args))]).expand(tensorproduct=True)
        return qapply_Mul(e.func(*args), **options)*result

    # Now try to actually apply the operator and build an inner product.
    try:
        result = lhs._apply_operator(rhs, **options)
    except (NotImplementedError, AttributeError):
        try:
            result = rhs._apply_operator(lhs, **options)
        except (NotImplementedError, AttributeError):
            if isinstance(lhs, BraBase) and isinstance(rhs, KetBase):
                result = InnerProduct(lhs, rhs)
                if ip_doit:
                    result = result.doit()
            else:
                result = None

    # TODO: I may need to expand before returning the final result.
    if result == 0:
        return S.Zero
    elif result is None:
        if len(args) == 0:
            # We had two args to begin with so args=[].
            return e
        else:
            return qapply_Mul(e.func(*(args + [lhs])), **options)*rhs
    elif isinstance(result, InnerProduct):
        return result*qapply_Mul(e.func(*args), **options)
    else:  # result is a scalar times a Mul, Add or TensorProduct
        return qapply(e.func(*args)*result, **options)
