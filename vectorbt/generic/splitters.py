"""Splitters for cross-validation.

Defines splitter classes similar (but may not compatible) to `sklearn.model_selection.BaseCrossValidator`."""

import numpy as np
import pandas as pd
import math

from vectorbt.base.index_fns import find_first_occurrence


class BaseSplitter:
    """Abstract splitter class."""

    def split(self, X, **kwargs):
        raise NotImplementedError


def split_ranges_into_sets(start_idxs, end_idxs, set_lens=(), left_to_right=True):
    """Generate ranges between each in `start_idxs` and `end_idxs` and
    optionally split into one or more sets.

    Args:
        start_idxs (array_like): Absolute start indices.
        end_idxs (array_like): Absolute end indices.
        set_lens (tuple or list of tuple): Lengths of sets in each range.

            The number of returned sets is the length of `set_lens` plus one,
            which stores the remaining elements.
        left_to_right (bool or list of bool): Whether to resolve `set_lens` from left to right.

            Makes the last set variable, otherwise makes the first set variable.

    ## Example

    * `set_lens=(0.5)`: 50% in training set, the rest in test set
    * `set_lens=(0.5, 0.25)`: 50% in training set, 25% in validation set, the rest in test set
    * `set_lens=(50, 30)`: 50 in training set, 30 in validation set, the rest in test set
    * `set_lens=(50, 30)` and `left_to_right=False`: 30 in test set, 50 in validation set,
        the rest in training set
    """

    for i in range(len(start_idxs)):
        start_idx = start_idxs[i]
        end_idx = end_idxs[i]

        range_len = end_idx - start_idx + 1
        new_set_lens = []
        if len(set_lens) == 0:
            yield (np.arange(start_idx, end_idx + 1),)
        else:
            if isinstance(set_lens[0], (tuple, list)):
                _set_lens = set_lens[i]
            else:
                _set_lens = set_lens
            if isinstance(left_to_right, (tuple, list)):
                _left_to_right = left_to_right[i]
            else:
                _left_to_right = left_to_right
            for j, set_len in enumerate(_set_lens):
                if 0 < set_len < 1:
                    set_len = math.floor(set_len * range_len)
                if set_len == 0:
                    raise ValueError(f"Set {j} in the range {i} is empty")
                new_set_lens.append(set_len)
            if sum(new_set_lens) < range_len:
                if _left_to_right:
                    new_set_lens = new_set_lens + [range_len - sum(new_set_lens)]
                else:
                    new_set_lens = [range_len - sum(new_set_lens)] + new_set_lens
            else:
                raise ValueError(f"Range of length {range_len} too short to split into {len(_set_lens) + 1} sets")

            # Split each range into sets
            idx_offset = 0
            set_ranges = []
            for set_len in new_set_lens:
                new_idx_offset = idx_offset + set_len
                set_ranges.append(np.arange(start_idx + idx_offset, start_idx + new_idx_offset))
                idx_offset = new_idx_offset

            yield tuple(set_ranges)


class RangeSplitter(BaseSplitter):
    """Range splitter."""

    def split(self, X, n=None, range_len=None, min_len=1, start_idxs=None, end_idxs=None, **kwargs):
        """Either split into `n` ranges each `range_len` long, or split into ranges between
        `start_idxs` and `end_idxs`, and concatenate along the column axis.

        At least one of `range_len`, `n`, or `start_idxs` and `end_idxs` must be set:

        * If `range_len` is None, are split evenly into `n` ranges.
        * If `n` is None, returns the maximum number of ranges of length `range_len` (can be a percentage).
        * If `start_idxs` and `end_idxs`, splits into ranges between both arrays.
        Both index arrays should be either NumPy arrays with absolute positions or
        pandas indexes with labels. The last index should be inclusive. The distance
        between each start and end index can be different, and smaller ranges are filled with NaNs.

        `**kwargs` are passed to `split_ranges_into_sets`."""
        if isinstance(X, (pd.Series, pd.DataFrame)):
            index = X.index
        else:
            index = pd.Index(np.arange(X.shape[0]))

        # Resolve start_idxs and end_idxs
        if start_idxs is None and end_idxs is None:
            if range_len is None and n is None:
                raise ValueError("At least n, range_len, or start_idxs and end_idxs must be set")
            if range_len is None:
                range_len = len(index) // n
            if 0 < range_len < 1:
                range_len = math.floor(range_len * len(index))
            start_idxs = np.arange(len(index) - range_len + 1)
            end_idxs = np.arange(range_len - 1, len(index))
        elif start_idxs is None or end_idxs is None:
            raise ValueError("Both start_idxs and end_idxs must be set")
        else:
            if isinstance(start_idxs, pd.Index):
                start_idxs = np.asarray([find_first_occurrence(idx, index) for idx in start_idxs])
            else:
                start_idxs = np.asarray(start_idxs)
            if isinstance(end_idxs, pd.Index):
                end_idxs = np.asarray([find_first_occurrence(idx, index) for idx in end_idxs])
            else:
                end_idxs = np.asarray(end_idxs)

        # Filter out short ranges
        start_idxs, end_idxs = np.broadcast_arrays(start_idxs, end_idxs)
        range_lens = end_idxs - start_idxs + 1
        min_len_mask = range_lens >= min_len
        if not np.any(min_len_mask):
            raise ValueError(f"There are no ranges that meet range_len>={min_len}")
        start_idxs = start_idxs[min_len_mask]
        end_idxs = end_idxs[min_len_mask]

        # Evenly select n ranges
        if n is not None:
            if n > len(start_idxs):
                raise ValueError(f"n cannot be bigger than the maximum number of ranges {len(start_idxs)}")
            idxs = np.round(np.linspace(0, len(start_idxs) - 1, n)).astype(int)
            start_idxs = start_idxs[idxs]
            end_idxs = end_idxs[idxs]

        return split_ranges_into_sets(start_idxs, end_idxs, **kwargs)


class RollingSplitter(BaseSplitter):
    """Rolling walk-forward splitter."""

    def split(self, X, n=None, window_len=None, min_len=1, **kwargs):
        """Split by rolling a window.

        `**kwargs` are passed to `split_ranges_into_sets`."""
        if isinstance(X, (pd.Series, pd.DataFrame)):
            index = X.index
        else:
            index = pd.Index(np.arange(X.shape[0]))

        # Resolve start_idxs and end_idxs
        if window_len is None and n is None:
            raise ValueError("At least n or window_len must be set")
        if window_len is None:
            window_len = len(index) // n
        if 0 < window_len < 1:
            window_len = math.floor(window_len * len(index))
        start_idxs = np.arange(len(index) - window_len + 1)
        end_idxs = np.arange(window_len - 1, len(index))

        # Filter out short ranges
        window_lens = end_idxs - start_idxs + 1
        min_len_mask = window_lens >= min_len
        if not np.any(min_len_mask):
            raise ValueError(f"There are no ranges that meet window_len>={min_len}")
        start_idxs = start_idxs[min_len_mask]
        end_idxs = end_idxs[min_len_mask]

        # Evenly select n ranges
        if n is not None:
            if n > len(start_idxs):
                raise ValueError(f"n cannot be bigger than the maximum number of windows {len(start_idxs)}")
            idxs = np.round(np.linspace(0, len(start_idxs) - 1, n)).astype(int)
            start_idxs = start_idxs[idxs]
            end_idxs = end_idxs[idxs]

        return split_ranges_into_sets(start_idxs, end_idxs, **kwargs)


class ExpandingSplitter(BaseSplitter):
    """Expanding walk-forward splitter."""

    def split(self, X, n=None, min_len=1, **kwargs):
        """Similar to `RollingSplitter.split`, but expanding.

        `**kwargs` are passed to `split_ranges_into_sets`."""
        if isinstance(X, (pd.Series, pd.DataFrame)):
            index = X.index
        else:
            index = pd.Index(np.arange(X.shape[0]))

        # Resolve start_idxs and end_idxs
        start_idxs = np.full(len(index), 0)
        end_idxs = np.arange(len(index))

        # Filter out short ranges
        window_lens = end_idxs - start_idxs + 1
        min_len_mask = window_lens >= min_len
        if not np.any(min_len_mask):
            raise ValueError(f"There are no ranges that meet window_len>={min_len}")
        start_idxs = start_idxs[min_len_mask]
        end_idxs = end_idxs[min_len_mask]

        # Evenly select n ranges
        if n is not None:
            if n > len(start_idxs):
                raise ValueError(f"n cannot be bigger than the maximum number of windows {len(start_idxs)}")
            idxs = np.round(np.linspace(0, len(start_idxs) - 1, n)).astype(int)
            start_idxs = start_idxs[idxs]
            end_idxs = end_idxs[idxs]

        return split_ranges_into_sets(start_idxs, end_idxs, **kwargs)
