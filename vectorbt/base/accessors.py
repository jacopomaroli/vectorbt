"""Custom pandas accessors.

Methods can be accessed as follows:

* `BaseSRAccessor` -> `pd.Series.vbt.*`
* `BaseDFAccessor` -> `pd.DataFrame.vbt.*`

For example:

```python-repl
>>> import pandas as pd
>>> import vectorbt as vbt

>>> # vectorbt.base.accessors.BaseAccessor.make_symmetric
>>> pd.Series([1, 2, 3]).vbt.make_symmetric()
     0    1    2
0  1.0  2.0  3.0
1  2.0  NaN  NaN
2  3.0  NaN  NaN
```

It contains base methods for working with pandas objects. Most of these methods are adaptations
of combine/reshape/index functions that can work with pandas objects. For example,
`vectorbt.base.reshape_fns.broadcast` can take an arbitrary number of pandas objects, thus
you can find its variations as accessor methods.

```python-repl
>>> sr = pd.Series([1])
>>> df = pd.DataFrame([1, 2, 3])

>>> vbt.base.reshape_fns.broadcast_to(sr, df)
   0
0  1
1  1
2  1
>>> sr.vbt.broadcast_to(df)
   0
0  1
1  1
2  1
```

Additionally, `BaseAccessor` implements arithmetic (such as `+`), comparison (such as `>`) and
logical operators (such as `&`) by doing 1) NumPy-like broadcasting and 2) the compuation with NumPy
under the hood, which is mostly much faster than with pandas.

```python-repl
>>> df = pd.DataFrame(np.random.uniform(size=(1000, 1000)))

>>> %timeit df * 2  # pandas
296 ms ± 27.4 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
>>> %timeit df.vbt * 2  # vectorbt
5.48 ms ± 1.12 ms per loop (mean ± std. dev. of 7 runs, 100 loops each)
```

!!! note
    You should ensure that your `*.vbt` operand is on the left if the other operand is an array.

    Accessors do not utilize caching."""

import numpy as np
import pandas as pd
from collections.abc import Iterable

from vectorbt.utils import checks
from vectorbt.utils.decorators import class_or_instancemethod
from vectorbt.utils.config import merge_dicts
from vectorbt.base import combine_fns, index_fns, reshape_fns
from vectorbt.base.array_wrapper import ArrayWrapper
from vectorbt.base.class_helpers import (
    add_binary_magic_methods,
    add_unary_magic_methods,
    binary_magic_methods,
    unary_magic_methods
)


@add_binary_magic_methods(
    binary_magic_methods,
    lambda self, other, np_func: self.combine(other, allow_multiple=False, combine_func=np_func)
)
@add_unary_magic_methods(
    unary_magic_methods,
    lambda self, np_func: self.apply(apply_func=np_func)
)
class BaseAccessor:
    """Accessor on top of Series and DataFrames.

    Accessible through `pd.Series.vbt` and `pd.DataFrame.vbt`, and all child accessors.

    Series is just a DataFrame with one column, hence to avoid defining methods exclusively for 1-dim data,
    we will convert any Series to a DataFrame and perform matrix computation on it. Afterwards,
    by using `BaseAccessor.wrapper`, we will convert the 2-dim output back to a Series.

    `**kwargs` will be passed to `vectorbt.base.array_wrapper.ArrayWrapper`."""

    def __init__(self, obj, **kwargs):
        if not checks.is_pandas(obj):  # parent accessor
            obj = obj._obj
        self._obj = obj
        self._wrapper = ArrayWrapper.from_obj(obj, **kwargs)

    def __call__(self, *args, **kwargs):
        """Allows passing arguments to the initializer."""

        return self.__class__(self._obj, *args, **kwargs)

    @property
    def wrapper(self):
        """Array wrapper."""
        return self._wrapper

    # ############# Creation ############# #

    @classmethod
    def empty(cls, shape, fill_value=np.nan, **kwargs):
        """Generate an empty Series/DataFrame of shape `shape` and fill with `fill_value`."""
        if not isinstance(shape, tuple) or (isinstance(shape, tuple) and len(shape) == 1):
            return pd.Series(np.full(shape, fill_value), **kwargs)
        return pd.DataFrame(np.full(shape, fill_value), **kwargs)

    @classmethod
    def empty_like(cls, other, fill_value=np.nan, **kwargs):
        """Generate an empty Series/DataFrame like `other` and fill with `fill_value`."""
        if checks.is_series(other):
            return cls.empty(other.shape, fill_value=fill_value, index=other.index, name=other.name, **kwargs)
        return cls.empty(other.shape, fill_value=fill_value, index=other.index, columns=other.columns, **kwargs)

    # ############# Index and columns ############# #

    def apply_on_index(self, apply_func, *args, axis=1, inplace=False, **kwargs):
        """Apply function `apply_func` on index of the pandas object.

        Set `axis` to 1 for columns and 0 for index.
        If `inplace` is True, modifies the pandas object. Otherwise, returns a copy."""
        checks.assert_in(axis, (0, 1))

        if axis == 1:
            obj_index = self.wrapper.columns
        else:
            obj_index = self.wrapper.index
        obj_index = apply_func(obj_index, *args, **kwargs)
        if inplace:
            if axis == 1:
                self._obj.columns = obj_index
            else:
                self._obj.index = obj_index
            return None
        else:
            obj = self._obj.copy()
            if axis == 1:
                obj.columns = obj_index
            else:
                obj.index = obj_index
            return obj

    def stack_index(self, index, on_top=True, axis=1, inplace=False, **kwargs):
        """See `vectorbt.base.index_fns.stack_indexes`.

        Set `on_top` to False to stack at bottom.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            if on_top:
                return index_fns.stack_indexes([index, obj_index], **kwargs)
            return index_fns.stack_indexes([obj_index, index], **kwargs)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    def drop_levels(self, levels, axis=1, inplace=False):
        """See `vectorbt.base.index_fns.drop_levels`.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            return index_fns.drop_levels(obj_index, levels)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    def rename_levels(self, name_dict, axis=1, inplace=False):
        """See `vectorbt.base.index_fns.rename_levels`.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            return index_fns.rename_levels(obj_index, name_dict)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    def select_levels(self, level_names, axis=1, inplace=False):
        """See `vectorbt.base.index_fns.select_levels`.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            return index_fns.select_levels(obj_index, level_names)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    def drop_redundant_levels(self, axis=1, inplace=False):
        """See `vectorbt.base.index_fns.drop_redundant_levels`.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            return index_fns.drop_redundant_levels(obj_index)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    def drop_duplicate_levels(self, keep='last', axis=1, inplace=False):
        """See `vectorbt.base.index_fns.drop_duplicate_levels`.

        See `BaseAccessor.apply_on_index` for other keyword arguments."""

        def apply_func(obj_index):
            return index_fns.drop_duplicate_levels(obj_index, keep=keep)

        return self.apply_on_index(apply_func, axis=axis, inplace=inplace)

    # ############# Reshaping ############# #

    def to_1d_array(self):
        """Convert to 1-dim NumPy array

        See `vectorbt.base.reshape_fns.to_1d`."""
        return reshape_fns.to_1d(self._obj, raw=True)

    def to_2d_array(self):
        """Convert to 2-dim NumPy array.

        See `vectorbt.base.reshape_fns.to_2d`."""
        return reshape_fns.to_2d(self._obj, raw=True)

    def tile(self, n, keys=None, axis=1, wrap_kwargs=None):
        """See `vectorbt.base.reshape_fns.tile`.

        Set `axis` to 1 for columns and 0 for index.
        Use `keys` as the outermost level."""
        tiled = reshape_fns.tile(self._obj, n, axis=axis)
        if keys is not None:
            if axis == 1:
                new_columns = index_fns.combine_indexes([keys, self.wrapper.columns])
                return tiled.vbt.wrapper.wrap(
                    tiled.values, **merge_dicts(dict(columns=new_columns), wrap_kwargs))
            else:
                new_index = index_fns.combine_indexes([keys, self.wrapper.index])
                return tiled.vbt.wrapper.wrap(
                    tiled.values, **merge_dicts(dict(index=new_index), wrap_kwargs))
        return tiled

    def repeat(self, n, keys=None, axis=1, wrap_kwargs=None):
        """See `vectorbt.base.reshape_fns.repeat`.

        Set `axis` to 1 for columns and 0 for index.
        Use `keys` as the outermost level."""
        repeated = reshape_fns.repeat(self._obj, n, axis=axis)
        if keys is not None:
            if axis == 1:
                new_columns = index_fns.combine_indexes([self.wrapper.columns, keys])
                return repeated.vbt.wrapper.wrap(
                    repeated.values, **merge_dicts(dict(columns=new_columns), wrap_kwargs))
            else:
                new_index = index_fns.combine_indexes([self.wrapper.index, keys])
                return repeated.vbt.wrapper.wrap(
                    repeated.values, **merge_dicts(dict(index=new_index), wrap_kwargs))
        return repeated

    def align_to(self, other, wrap_kwargs=None):
        """Align to `other` on their axes.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt
        >>> import pandas as pd

        >>> df1 = pd.DataFrame([[1, 2], [3, 4]], index=['x', 'y'], columns=['a', 'b'])
        >>> df1
           a  b
        x  1  2
        y  3  4

        >>> df2 = pd.DataFrame([[5, 6, 7, 8], [9, 10, 11, 12]], index=['x', 'y'],
        ...     columns=pd.MultiIndex.from_arrays([[1, 1, 2, 2], ['a', 'b', 'a', 'b']]))
        >>> df2
               1       2
           a   b   a   b
        x  5   6   7   8
        y  9  10  11  12

        >>> df1.vbt.align_to(df2)
              1     2
           a  b  a  b
        x  1  2  1  2
        y  3  4  3  4
        ```
        """
        checks.assert_type(other, (pd.Series, pd.DataFrame))
        obj = reshape_fns.to_2d(self._obj)
        other = reshape_fns.to_2d(other)

        aligned_index = index_fns.align_index_to(obj.index, other.index)
        aligned_columns = index_fns.align_index_to(obj.columns, other.columns)
        obj = obj.iloc[aligned_index, aligned_columns]
        return self.wrapper.wrap(
            obj.values, group_by=False,
            **merge_dicts(dict(index=other.index, columns=other.columns), wrap_kwargs))

    @class_or_instancemethod
    def broadcast(self_or_cls, *others, **kwargs):
        """See `vectorbt.base.reshape_fns.broadcast`."""
        others = tuple(map(lambda x: x._obj if isinstance(x, BaseAccessor) else x, others))
        if isinstance(self_or_cls, type):
            return reshape_fns.broadcast(*others, **kwargs)
        return reshape_fns.broadcast(self_or_cls._obj, *others, **kwargs)

    def broadcast_to(self, other, **kwargs):
        """See `vectorbt.base.reshape_fns.broadcast_to`."""
        if isinstance(other, BaseAccessor):
            other = other._obj
        return reshape_fns.broadcast_to(self._obj, other, **kwargs)

    def make_symmetric(self):  # pragma: no cover
        """See `vectorbt.base.reshape_fns.make_symmetric`."""
        return reshape_fns.make_symmetric(self._obj)

    def unstack_to_array(self, **kwargs):  # pragma: no cover
        """See `vectorbt.base.reshape_fns.unstack_to_array`."""
        return reshape_fns.unstack_to_array(self._obj, **kwargs)

    def unstack_to_df(self, **kwargs):  # pragma: no cover
        """See `vectorbt.base.reshape_fns.unstack_to_df`."""
        return reshape_fns.unstack_to_df(self._obj, **kwargs)

    # ############# Combining ############# #

    def apply(self, *args, apply_func=None, keep_pd=False, to_2d=False, wrap_kwargs=None, **kwargs):
        """Apply a function `apply_func`.

        Args:
            *args: Variable arguments passed to `apply_func`.
            apply_func (callable): Apply function.

                Can be Numba-compiled.
            keep_pd (bool): Whether to keep inputs as pandas objects, otherwise convert to NumPy arrays.
            to_2d (bool): Whether to reshape inputs to 2-dim arrays, otherwise keep as-is.
            wrap_kwargs (dict): Keyword arguments passed to `vectorbt.base.array_wrapper.ArrayWrapper.wrap`.
            **kwargs: Keyword arguments passed to `combine_func`.

        !!! note
            The resulted array must have the same shape as the original array.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt
        >>> import pandas as pd

        >>> sr = pd.Series([1, 2], index=['x', 'y'])
        >>> sr2.vbt.apply(apply_func=lambda x: x ** 2)
        i2
        x2    1
        y2    4
        z2    9
        Name: a2, dtype: int64
        ```
        """
        checks.assert_not_none(apply_func)
        # Optionally cast to 2d array
        if to_2d:
            obj = reshape_fns.to_2d(self._obj, raw=not keep_pd)
        else:
            if not keep_pd:
                obj = np.asarray(self._obj)
            else:
                obj = self._obj
        result = apply_func(obj, *args, **kwargs)
        return self.wrapper.wrap(result, group_by=False, **merge_dicts({}, wrap_kwargs))

    @class_or_instancemethod
    def concat(self_or_cls, *others, broadcast_kwargs=None, keys=None):
        """Concatenate with `others` along columns.

        Args:
            others (list of array_like): List of objects to be concatenated with this array.
            broadcast_kwargs (dict): Keyword arguments passed to `vectorbt.base.reshape_fns.broadcast`.
            keys (list of str or pd.Index): Outermost column level.
            convert_dtypes (bool): Whether to convert to inferred data types.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt
        >>> import pandas as pd

        >>> sr = pd.Series([1, 2], index=['x', 'y'])
        >>> df = pd.DataFrame([[3, 4], [5, 6]], index=['x', 'y'], columns=['a', 'b'])
        >>> sr.vbt.concat(df, keys=['c', 'd'])
              c     d
           a  b  a  b
        x  1  1  3  4
        y  2  2  5  6
        ```
        """
        others = tuple(map(lambda x: x._obj if isinstance(x, BaseAccessor) else x, others))
        if isinstance(self_or_cls, type):
            objs = others
        else:
            objs = (self_or_cls._obj,) + others
        if broadcast_kwargs is None:
            broadcast_kwargs = {}
        broadcasted = reshape_fns.broadcast(*objs, **broadcast_kwargs)
        broadcasted = tuple(map(reshape_fns.to_2d, broadcasted))
        out = pd.concat(broadcasted, axis=1, keys=keys)
        if not isinstance(out.columns, pd.MultiIndex) and np.all(out.columns == 0):
            out.columns = pd.RangeIndex(start=0, stop=len(out.columns), step=1)
        return out

    def apply_and_concat(self, ntimes, *args, apply_func=None, keep_pd=False, to_2d=False,
                         numba_loop=False, use_ray=False, keys=None, wrap_kwargs=None, **kwargs):
        """Apply `apply_func` `ntimes` times and concatenate the results along columns.
        See `vectorbt.base.combine_fns.apply_and_concat_one`.

        Args:
            ntimes (int): Number of times to call `apply_func`.
            *args: Variable arguments passed to `apply_func`.
            apply_func (callable): Apply function.

                Can be Numba-compiled.
            keep_pd (bool): Whether to keep inputs as pandas objects, otherwise convert to NumPy arrays.
            to_2d (bool): Whether to reshape inputs to 2-dim arrays, otherwise keep as-is.
            numba_loop (bool): Whether to loop using Numba.

                Set to True when iterating large number of times over small input,
                but note that Numba doesn't support variable keyword arguments.
            use_ray (bool): Whether to use Ray to execute `combine_func` in parallel.

                Only works with `numba_loop` set to False and `concat` is set to True.
                See `vectorbt.base.combine_fns.ray_apply` for related keyword arguments.
            keys (list of str or pd.Index): Outermost column level.
            wrap_kwargs (dict): Keyword arguments passed to `vectorbt.base.array_wrapper.ArrayWrapper.wrap`.
            **kwargs: Keyword arguments passed to `combine_func`.

        !!! note
            The resulted arrays to be concatenated must have the same shape as broadcast input arrays.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt
        >>> import pandas as pd

        >>> df = pd.DataFrame([[3, 4], [5, 6]], index=['x', 'y'], columns=['a', 'b'])
        >>> df.vbt.apply_and_concat(3, [1, 2, 3],
        ...     apply_func=lambda i, a, b: a * b[i], keys=['c', 'd', 'e'])
              c       d       e
           a  b   a   b   a   b
        x  3  4   6   8   9  12
        y  5  6  10  12  15  18
        ```

        Use Ray for small inputs and large processing times:

        ```python-repl
        >>> def apply_func(i, a):
        ...     time.sleep(1)
        ...     return a

        >>> sr = pd.Series([1, 2, 3])

        >>> %timeit sr.vbt.apply_and_concat(3, apply_func=apply_func)
        3.01 s ± 2.15 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

        >>> %timeit sr.vbt.apply_and_concat(3, apply_func=apply_func, use_ray=True)
        1.01 s ± 2.31 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
        ```
        """
        checks.assert_not_none(apply_func)
        # Optionally cast to 2d array
        if to_2d:
            obj = reshape_fns.to_2d(self._obj, raw=not keep_pd)
        else:
            if not keep_pd:
                obj = np.asarray(self._obj)
            else:
                obj = self._obj
        if checks.is_numba_func(apply_func) and numba_loop:
            if use_ray:
                raise ValueError("Ray cannot be used within Numba")
            result = combine_fns.apply_and_concat_one_nb(ntimes, apply_func, obj, *args, **kwargs)
        else:
            if use_ray:
                result = combine_fns.apply_and_concat_one_ray(ntimes, apply_func, obj, *args, **kwargs)
            else:
                result = combine_fns.apply_and_concat_one(ntimes, apply_func, obj, *args, **kwargs)
        # Build column hierarchy
        if keys is not None:
            new_columns = index_fns.combine_indexes([keys, self.wrapper.columns])
        else:
            top_columns = pd.Index(np.arange(ntimes), name='apply_idx')
            new_columns = index_fns.combine_indexes([top_columns, self.wrapper.columns])
        return self.wrapper.wrap(result, group_by=False, **merge_dicts(dict(columns=new_columns), wrap_kwargs))

    def combine(self, other, *args, allow_multiple=True, combine_func=None, keep_pd=False, to_2d=False,
                concat=False, numba_loop=False, use_ray=False, broadcast=True, broadcast_kwargs=None,
                keys=None, wrap_kwargs=None, **kwargs):
        """Combine with `other` using `combine_func`.

        Args:
            other (array_like or tuple of array_like): Object to combine this array with.
            *args: Variable arguments passed to `combine_func`.
            allow_multiple (bool): Whether a tuple/list will be considered as multiple objects in `other`.
            combine_func (callable): Function to combine two arrays.

                Can be Numba-compiled.
            keep_pd (bool): Whether to keep inputs as pandas objects, otherwise convert to NumPy arrays.
            to_2d (bool): Whether to reshape inputs to 2-dim arrays, otherwise keep as-is.
            concat (bool): Whether to concatenate the results along the column axis.
                therwise, pairwise combine into a Series/DataFrame of the same shape.

                If True, see `vectorbt.base.combine_fns.combine_and_concat`.
                If False, see `vectorbt.base.combine_fns.combine_multiple`.
            numba_loop (bool): Whether to loop using Numba.

                Set to True when iterating large number of times over small input,
                but note that Numba doesn't support variable keyword arguments.
            use_ray (bool): Whether to use Ray to execute `combine_func` in parallel.

                Only works with `numba_loop` set to False and `concat` is set to True.
                See `vectorbt.base.combine_fns.ray_apply` for related keyword arguments.
            broadcast (bool): Whether to broadcast all inputs.
            broadcast_kwargs (dict): Keyword arguments passed to `vectorbt.base.reshape_fns.broadcast`.
            keys (list of str or pd.Index): Outermost column level.
            wrap_kwargs (dict): Keyword arguments passed to `vectorbt.base.array_wrapper.ArrayWrapper.wrap`.
            **kwargs: Keyword arguments passed to `combine_func`.

        !!! note
            If `combine_func` is Numba-compiled, will broadcast using `WRITEABLE` and `C_CONTIGUOUS`
            flags, which can lead to an expensive computation overhead if passed objects are large and
            have different shape/memory order. You also must ensure that all objects have the same data type.

            Also remember to bring each in `*args` to a Numba-compatible format.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt
        >>> import pandas as pd

        >>> sr = pd.Series([1, 2], index=['x', 'y'])
        >>> df = pd.DataFrame([[3, 4], [5, 6]], index=['x', 'y'], columns=['a', 'b'])

        >>> sr.vbt.combine(df, combine_func=lambda x, y: x + y)
           a  b
        x  4  5
        y  7  8

        >>> sr.vbt.combine([df, df*2], combine_func=lambda x, y: x + y)
            a   b
        x  10  13
        y  17  20

        >>> sr.vbt.combine([df, df*2], combine_func=lambda x, y: x + y, concat=True, keys=['c', 'd'])
              c       d
           a  b   a   b
        x  4  5   7   9
        y  7  8  12  14
        ```

        Use Ray for small inputs and large processing times:

        ```python-repl
        >>> def combine_func(a, b):
        ...     time.sleep(1)
        ...     return a + b

        >>> sr = pd.Series([1, 2, 3])

        >>> %timeit sr.vbt.combine([1, 1, 1], combine_func=combine_func)
        3.01 s ± 2.98 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

        >>> %timeit sr.vbt.combine([1, 1, 1], combine_func=combine_func, concat=True, use_ray=True)
        1.02 s ± 2.32 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
        ```
        """
        if not allow_multiple or not isinstance(other, (tuple, list)):
            others = (other,)
        else:
            others = other
        others = tuple(map(lambda x: x._obj if isinstance(x, BaseAccessor) else x, others))
        checks.assert_not_none(combine_func)
        checks.assert_type(others, Iterable)
        # Broadcast arguments
        if broadcast:
            if broadcast_kwargs is None:
                broadcast_kwargs = {}
            if checks.is_numba_func(combine_func):
                # Numba requires writeable arrays
                # Plus all of our arrays must be in the same order
                broadcast_kwargs = merge_dicts(dict(require_kwargs=dict(requirements=['W', 'C'])), broadcast_kwargs)
            new_obj, *new_others = reshape_fns.broadcast(self._obj, *others, **broadcast_kwargs)
        else:
            new_obj, new_others = self._obj, others
        # Optionally cast to 2d array
        if to_2d:
            inputs = tuple(map(lambda x: reshape_fns.to_2d(x, raw=not keep_pd), (new_obj, *new_others)))
        else:
            if not keep_pd:
                inputs = tuple(map(lambda x: np.asarray(x), (new_obj, *new_others)))
            else:
                inputs = new_obj, *new_others
        if len(inputs) == 2:
            result = combine_func(inputs[0], inputs[1], *args, **kwargs)
            return new_obj.vbt.wrapper.wrap(result, **merge_dicts({}, wrap_kwargs))
        if concat:
            # Concat the results horizontally
            if checks.is_numba_func(combine_func) and numba_loop:
                if use_ray:
                    raise ValueError("Ray cannot be used within Numba")
                for i in range(1, len(inputs)):
                    checks.assert_meta_equal(inputs[i - 1], inputs[i])
                result = combine_fns.combine_and_concat_nb(
                    inputs[0], inputs[1:], combine_func, *args, **kwargs)
            else:
                if use_ray:
                    result = combine_fns.combine_and_concat_ray(
                        inputs[0], inputs[1:], combine_func, *args, **kwargs)
                else:
                    result = combine_fns.combine_and_concat(
                        inputs[0], inputs[1:], combine_func, *args, **kwargs)
            columns = new_obj.vbt.wrapper.columns
            if keys is not None:
                new_columns = index_fns.combine_indexes([keys, columns])
            else:
                top_columns = pd.Index(np.arange(len(new_others)), name='combine_idx')
                new_columns = index_fns.combine_indexes([top_columns, columns])
            return new_obj.vbt.wrapper.wrap(result, **merge_dicts(dict(columns=new_columns), wrap_kwargs))
        else:
            # Combine arguments pairwise into one object
            if use_ray:
                raise ValueError("Ray cannot be used with concat=False")
            if checks.is_numba_func(combine_func) and numba_loop:
                for i in range(1, len(inputs)):
                    checks.assert_dtype_equal(inputs[i - 1], inputs[i])
                result = combine_fns.combine_multiple_nb(inputs, combine_func, *args, **kwargs)
            else:
                result = combine_fns.combine_multiple(inputs, combine_func, *args, **kwargs)
            return new_obj.vbt.wrapper.wrap(result, **merge_dicts({}, wrap_kwargs))


class BaseSRAccessor(BaseAccessor):
    """Accessor on top of Series.

    Accessible through `pd.Series.vbt` and all child accessors."""

    def __init__(self, obj, **kwargs):
        if not checks.is_pandas(obj):  # parent accessor
            obj = obj._obj
        checks.assert_type(obj, pd.Series)

        BaseAccessor.__init__(self, obj, **kwargs)

    @class_or_instancemethod
    def is_series(self_or_cls):
        return True

    @class_or_instancemethod
    def is_frame(self_or_cls):
        return False


class BaseDFAccessor(BaseAccessor):
    """Accessor on top of DataFrames.

    Accessible through `pd.DataFrame.vbt` and all child accessors."""

    def __init__(self, obj, **kwargs):
        if not checks.is_pandas(obj):  # parent accessor
            obj = obj._obj
        checks.assert_type(obj, pd.DataFrame)

        BaseAccessor.__init__(self, obj, **kwargs)

    @class_or_instancemethod
    def is_series(self_or_cls):
        return False

    @class_or_instancemethod
    def is_frame(self_or_cls):
        return True
