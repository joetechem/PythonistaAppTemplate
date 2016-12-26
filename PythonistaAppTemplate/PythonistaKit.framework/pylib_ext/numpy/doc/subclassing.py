#\input texinfo

"""
=============================
Subclassing ndarray in python
=============================

Credits
-------

This page is based with thanks on the wiki page on subclassing by Pierre
Gerard-Marchant - http://www.scipy.org/Subclasses.

Introduction
------------

Subclassing ndarray is relatively simple, but it has some complications
compared to other Python objects.  On this page we explain the machinery
that allows you to subclass ndarray, and the implications for
implementing a subclass.

ndarrays and object creation
============================

Subclassing ndarray is complicated by the fact that new instances of
ndarray classes can come about in three different ways.  These are:

#. Explicit constructor call - as in ``MySubClass(params)``.  This is
   the usual route to Python instance creation.
#. View casting - casting an existing ndarray as a given subclass
#. New from template - creating a new instance from a template
   instance. Examples include returning slices from a subclassed array,
   creating return types from ufuncs, and copying arrays.  See
   :ref:`new-from-template` for more details

The last two are characteristics of ndarrays - in order to support
things like array slicing.  The complications of subclassing ndarray are
due to the mechanisms numpy has to support these latter two routes of
instance creation.

.. _view-casting:

View casting
------------

*View casting* is the standard ndarray mechanism by which you take an
ndarray of any subclass, and return a view of the array as another
(specified) subclass:

>>> import numpy as np
>>> # create a completely useless ndarray subclass
>>> class C(np.ndarray): pass
>>> # create a standard ndarray
>>> arr = np.zeros((3,))
>>> # take a view of it, as our useless subclass
>>> c_arr = arr.view(C)
>>> type(c_arr)
<class 'C'>

.. _new-from-template:

Creating new from template
--------------------------

New instances of an ndarray subclass can also come about by a very
similar mechanism to :ref:`view-casting`, when numpy finds it needs to
create a new instance from a template instance.  The most obvious place
this has to happen is when you are taking slices of subclassed arrays.
For example:

>>> v = c_arr[1:]
>>> type(v) # the view is of type 'C'
<class 'C'>
>>> v is c_arr # but it's a new instance
False

The slice is a *view* onto the original ``c_arr`` data.  So, when we
take a view from the ndarray, we return a new ndarray, of the same
class, that points to the data in the original.

There are other points in the use of ndarrays where we need such views,
such as copying arrays (``c_arr.copy()``), creating ufunc output arrays
(see also :ref:`array-wrap`), and reducing methods (like
``c_arr.mean()``.

Relationship of view casting and new-from-template
--------------------------------------------------

These paths both use the same machinery.  We make the distinction here,
because they result in different input to your methods.  Specifically,
:ref:`view-casting` means you have created a new instance of your array
type from any potential subclass of ndarray.  :ref:`new-from-template`
means you have created a new instance of your class from a pre-existing
instance, allowing you - for example - to copy across attributes that
are particular to your subclass.

Implications for subclassing
----------------------------

If we subclass ndarray, we need to deal not only with explicit
construction of our array type, but also :ref:`view-casting` or
:ref:`new-from-template`.  Numpy has the machinery to do this, and this
machinery that makes subclassing slightly non-standard.

There are two aspects to the machinery that ndarray uses to support
views and new-from-template in subclasses.

The first is the use of the ``ndarray.__new__`` method for the main work
of object initialization, rather then the more usual ``__init__``
method.  The second is the use of the ``__array_finalize__`` method to
allow subclasses to clean up after the creation of views and new
instances from templates.

A brief Python primer on ``__new__`` and ``__init__``
=====================================================

``__new__`` is a standard Python method, and, if present, is called
before ``__init__`` when we create a class instance. See the `python
__new__ documentation
<http://docs.python.org/reference/datamodel.html#object.__new__>`_ for more detail.

For example, consider the following Python code:

.. testcode::

  class C(object):
      def __new__(cls, *args):
          print 'Cls in __new__:', cls
          print 'Args in __new__:', args
          return object.__new__(cls, *args)

      def __init__(self, *args):
          print 'type(self) in __init__:', type(self)
          print 'Args in __init__:', args

meaning that we get:

>>> c = C('hello')
Cls in __new__: <class 'C'>
Args in __new__: ('hello',)
type(self) in __init__: <class 'C'>
Args in __init__: ('hello',)

When we call ``C('hello')``, the ``__new__`` method gets its own class
as first argument, and the passed argument, which is the string
``'hello'``.  After python calls ``__new__``, it usually (see below)
calls our ``__init__`` method, with the output of ``__new__`` as the
first argument (now a class instance), and the passed arguments
following.

As you can see, the object can be initialized in the ``__new__``
method or the ``__init__`` method, or both, and in fact ndarray does
not have an ``__init__`` method, because all the initialization is
done in the ``__new__`` method.

Why use ``__new__`` rather than just the usual ``__init__``?  Because
in some cases, as for ndarray, we want to be able to return an object
of some other class.  Consider the following:

.. testcode::

  class D(C):
      def __new__(cls, *args):
          print 'D cls is:', cls
          print 'D args in __new__:', args
          return C.__new__(C, *args)

      def __init__(self, *args):
          # we never get here
          print 'In D __init__'

meaning that:

>>> obj = D('hello')
D cls is: <class 'D'>
D args in __new__: ('hello',)
Cls in __new__: <class 'C'>
Args in __new__: ('hello',)
>>> type(obj)
<class 'C'>

The definition of ``C`` is the same as before, but for ``D``, the
``__new__`` method returns an instance of class ``C`` rather than
``D``.  Note that the ``__init__`` method of ``D`` does not get
called.  In general, when the ``__new__`` method returns an object of
class other than the class in which it is defined, the ``__init__``
method of that class is not called.

This is how subclasses of the ndarray class are able to return views
that preserve the class type.  When taking a view, the standard
ndarray machinery creates the new ndarray object with something
like::

  obj = ndarray.__new__(subtype, shape, ...

where ``subdtype`` is the subclass.  Thus the returned view is of the
same class as the subclass, rather than being of class ``ndarray``.

That solves the problem of returning views of the same type, but now
we have a new problem.  The machinery of ndarray can set the class
this way, in its standard methods for taking views, but the ndarray
``__new__`` method knows nothing of what we have done in our own
``__new__`` method in order to set attributes, and so on.  (Aside -
why not call ``obj = subdtype.__new__(...`` then?  Because we may not
have a ``__new__`` method with the same call signature).

The role of ``__array_finalize__``
==================================

``__array_finalize__`` is the mechanism that numpy provides to allow
subclasses to handle the various ways that new instances get created.

Remember that subclass instances can come about in these three ways:

#. explicit constructor call (``obj = MySubClass(params)``).  This will
   call the usual sequence of ``MySubClass.__new__`` then (if it exists)
   ``MySubClass.__init__``.
#. :ref:`view-casting`
#. :ref:`new-from-template`

Our ``MySubClass.__new__`` method only gets called in the case of the
explicit constructor call, so we can't rely on ``MySubClass.__new__`` or
``MySubClass.__init__`` to deal with the view casting and
new-from-template.  It turns out that ``MySubClass.__array_finalize__``
*does* get called for all three methods of object creation, so this is
where our object creation housekeeping usually goes.

* For the explicit constructor call, our subclass will need to create a
  new ndarray instance of its own class.  In practice this means that
  we, the authors of the code, will need to make a call to
  ``ndarray.__new__(MySubClass,...)``, or do view casting of an existing
  array (see below)
* For view casting and new-from-template, the equivalent of
  ``ndarray.__new__(MySubClass,...`` is called, at the C level.

The arguments that ``__array_finalize__`` recieves differ for the three
methods of instance creation above.

The following code allows us to look at the call sequences and arguments:

.. testcode::

   import numpy as np

   class C(np.ndarray):
       def __new__(cls, *args, **kwargs):
           print 'In __new__ with class %s' % cls
           return np.ndarray.__new__(cls, *args, **kwargs)

       def __init__(self, *args, **kwargs):
           # in practice you probably will not need or want an __init__
           # method for your subclass
           print 'In __init__ with class %s' % self.__class__

       def __array_finalize__(self, obj):
           print 'In array_finalize:'
           print '   self type is %s' % type(self)
           print '   obj type is %s' % type(obj)


Now:

>>> # Explicit constructor
>>> c = C((10,))
In __new__ with class <class 'C'>
In array_finalize:
   self type is <class 'C'>
   obj type is <type 'NoneType'>
In __init__ with class <class 'C'>
>>> # View casting
>>> a = np.arange(10)
>>> cast_a = a.view(C)
In array_finalize:
   self type is <class 'C'>
   obj type is <type 'numpy.ndarray'>
>>> # Slicing (example of new-from-template)
>>> cv = c[:1]
In array_finalize:
   self type is <class 'C'>
   obj type is <class 'C'>

The signature of ``__array_finalize__`` is::

    def __array_finalize__(self, obj):

``ndarray.__new__`` passes ``__array_finalize__`` the new object, of our
own class (``self``) as well as the object from which the view has been
taken (``obj``).  As you can see from the output above, the ``self`` is
always a newly created instance of our subclass, and the type of ``obj``
differs for the three instance creation methods:

* When called from the explicit constructor, ``obj`` is ``None``
* When called from view casting, ``obj`` can be an instance of any
  subclass of ndarray, including our own.
* When called in new-from-template, ``obj`` is another instance of our
  own subclass, that we might use to update the new ``self`` instance.

Because ``__array_finalize__`` is the only method that always sees new
instances being created, it is the sensible place to fill in instance
defaults for new object attributes, among other tasks.

This may be clearer with an example.

Simple example - adding an extra attribute to ndarray
-----------------------------------------------------

.. testcode::

  import numpy as np

  class InfoArray(np.ndarray):

      def __new__(subtype, shape, dtype=float, buffer=None, offset=0,
            strides=None, order=None, info=None):
          # Create the ndarray instance of our type, given the usual
          # ndarray input arguments.  This will call the standard
          # ndarray constructor, but return an object of our type.
          # It also triggers a call to InfoArray.__array_finalize__
          obj = np.ndarray.__new__(subtype, shape, dtype, buffer, offset, strides,
                           order)
          # set the new 'info' attribute to the value passed
          obj.info = info
          # Finally, we must return the newly created object:
          return obj

      def __array_finalize__(self, obj):
          # ``self`` is a new object resulting from
          # ndarray.__new__(InfoArray, ...), therefore it only has
          # attributes that the ndarray.__new__ constructor gave it -
          # i.e. those of a standard ndarray.
          #
          # We could have got to the ndarray.__new__ call in 3 ways:
          # From an explicit constructor - e.g. InfoArray():
          #    obj is None
          #    (we're in the middle of the InfoArray.__new__
          #    constructor, and self.info will be set when we return to
          #    InfoArray.__new__)
          if obj is None: return
          # From view casting - e.g arr.view(InfoArray):
          #    obj is arr
          #    (type(obj) can be InfoArray)
          # From new-from-template - e.g infoarr[:3]
          #    type(obj) is InfoArray
          #
          # Note that it is here, rather than in the __new__ method,
          # that we set the default value for 'info', because this
          # method sees all creation of default objects - with the
          # InfoArray.__new__ constructor, but also with
          # arr.view(InfoArray).
          self.info = getattr(obj, 'info', None)
          # We do not need to return anything


Using the object looks like this:

  >>> obj = InfoArray(shape=(3,)) # explicit constructor
  >>> type(obj)
  <class 'InfoArray'>
  >>> obj.info is None
  True
  >>> obj = InfoArray(shape=(3,), info='information')
  >>> obj.info
  'information'
  >>> v = obj[1:] # new-from-template - here - slicing
  >>> type(v)
  <class 'InfoArray'>
  >>> v.info
  'information'
  >>> arr = np.arange(10)
  >>> cast_arr = arr.view(InfoArray) # view casting
  >>> type(cast_arr)
  <class 'InfoArray'>
  >>> cast_arr.info is None
  True

This class isn't very useful, because it has the same constructor as the
bare ndarray object, including passing in buffers and shapes and so on.
We would probably prefer the constructor to be able to take an already
formed ndarray from the usual numpy calls to ``np.array`` and return an
object.

Slightly more realistic example - attribute added to existing array
-------------------------------------------------------------------

Here is a class that takes a standard ndarray that already exists, casts
as our type, and adds an extra attribute.

.. testcode::

  import numpy as np

  class RealisticInfoArray(np.ndarray):

      def __new__(cls, input_array, info=None):
          # Input array is an already formed ndarray instance
          # We first cast to be our class type
          obj = np.asarray(input_array).view(cls)
          # add the new attribute to the created instance
          obj.info = info
          # Finally, we must return the newly created object:
          return obj

      def __array_finalize__(self, obj):
          # see InfoArray.__array_finalize__ for comments
          if obj is None: return
          self.info = getattr(obj, 'info', None)


So:

  >>> arr = np.arange(5)
  >>> obj = RealisticInfoArray(arr, info='information')
  >>> type(obj)
  <class 'RealisticInfoArray'>
  >>> obj.info
  'information'
  >>> v = obj[1:]
  >>> type(v)
  <class 'RealisticInfoArray'>
  >>> v.info
  'information'

.. _array-wrap:

``__array_wrap__`` for ufuncs
-------------------------------------------------------

``__array_wrap__`` gets called at the end of numpy ufuncs and other numpy
functions, to allow a subclass to set the type of the return value
and update attributes and metadata. Let's show how this works with an example.
First we make the same subclass as above, but with a different name and
some print statements:

.. testcode::

  import numpy as np

  class MySubClass(np.ndarray):

      def __new__(cls, input_array, info=None):
          obj = np.asarray(input_array).view(cls)
          obj.info = info
          return obj

      def __array_finalize__(self, obj):
          print 'In __array_finalize__:'
          print '   self is %s' % repr(self)
          print '   obj is %s' % repr(obj)
          if obj is None: return
          self.info = getattr(obj, 'info', None)

      def __array_wrap__(self, out_arr, context=None):
          print 'In __array_wrap__:'
          print '   self is %s' % repr(self)
          print '   arr is %s' % repr(out_arr)
          # then just call the parent
          return np.ndarray.__array_wrap__(self, out_arr, context)

We run a ufunc on an instance of our new array:

>>> obj = MySubClass(np.arange(5), info='spam')
In __array_finalize__:
   self is MySubClass([0, 1, 2, 3, 4])
   obj is array([0, 1, 2, 3, 4])
>>> arr2 = np.arange(5)+1
>>> ret = np.add(arr2, obj)
In __array_wrap__:
   self is MySubClass([0, 1, 2, 3, 4])
   arr is array([1, 3, 5, 7, 9])
In __array_finalize__:
   self is MySubClass([1, 3, 5, 7, 9])
   obj is MySubClass([0, 1, 2, 3, 4])
>>> ret
MySubClass([1, 3, 5, 7, 9])
>>> ret.info
'spam'

Note that the ufunc (``np.add``) has called the ``__array_wrap__`` method of the
input with the highest ``__array_priority__`` value, in this case
``MySubClass.__array_wrap__``, with arguments ``self`` as ``obj``, and
``out_arr`` as the (ndarray) result of the addition.  In turn, the
default ``__array_wrap__`` (``ndarray.__array_wrap__``) has cast the
result to class ``MySubClass``, and called ``__array_finalize__`` -
hence the copying of the ``info`` attribute.  This has all happened at the C level.

But, we could do anything we wanted:

.. testcode::

  class SillySubClass(np.ndarray):

      def __array_wrap__(self, arr, context=None):
          return 'I lost your data'

>>> arr1 = np.arange(5)
>>> obj = arr1.view(SillySubClass)
>>> arr2 = np.arange(5)
>>> ret = np.multiply(obj, arr2)
>>> ret
'I lost your data'

So, by defining a specific ``__array_wrap__`` method for our subclass,
we can tweak the output from ufuncs. The ``__array_wrap__`` method
requires ``self``, then an argument - which is the result of the ufunc -
and an optional parameter *context*. This parameter is returned by some
ufuncs as a 3-element tuple: (name of the ufunc, argument of the ufunc,
domain of the ufunc). ``__array_wrap__`` should return an instance of
its containing class.  See the masked array subclass for an
implementation.

In addition to ``__array_wrap__``, which is called on the way out of the
ufunc, there is also an ``__array_prepare__`` method which is called on
the way into the ufunc, after the output arrays are created but before any
computation has been performed. The default implementation does nothing
but pass through the array. ``__array_prepare__`` should not attempt to
access the array data or resize the array, it is intended for setting the
output array type, updating attributes and metadata, and performing any
checks based on the input that may be desired before computation begins.
Like ``__array_wrap__``, ``__array_prepare__`` must return an ndarray or
subclass thereof or raise an error.

Extra gotchas - custom ``__del__`` methods and ndarray.base
-----------------------------------------------------------

One of the problems that ndarray solves is keeping track of memory
ownership of ndarrays and their views.  Consider the case where we have
created an ndarray, ``arr`` and have taken a slice with ``v = arr[1:]``.
The two objects are looking at the same memory.  Numpy keeps track of
where the data came from for a particular array or view, with the
``base`` attribute:

>>> # A normal ndarray, that owns its own data
>>> arr = np.zeros((4,))
>>> # In this case, base is None
>>> arr.base is None
True
>>> # We take a view
>>> v1 = arr[1:]
>>> # base now points to the array that it derived from
>>> v1.base is arr
True
>>> # Take a view of a view
>>> v2 = v1[1:]
>>> # base points to the view it derived from
>>> v2.base is v1
True

In general, if the array owns its own memory, as for ``arr`` in this
case, then ``arr.base`` will be None - there are some exceptions to this
- see the numpy book for more details.

The ``base`` attribute is useful in being able to tell whether we have
a view or the original array.  This in turn can be useful if we need
to know whether or not to do some specific cleanup when the subclassed
array is deleted.  For example, we may only want to do the cleanup if
the original array is deleted, but not the views.  For an example of
how this can work, have a look at the ``memmap`` class in
``numpy.core``.


"""
from __future__ import division, absolute_import, print_function
