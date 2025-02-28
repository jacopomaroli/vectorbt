"""Class for mapping column arrays."""

from vectorbt.utils.decorators import cached_property, cached_method
from vectorbt.base.reshape_fns import to_1d
from vectorbt.records import nb


class ColumnMapper:
    """Used by `vectorbt.records.base.Records` and `vectorbt.records.mapped_array.MappedArray`
    classes to make use of column and group metadata."""
    def __init__(self, wrapper, col_arr):
        self._wrapper = wrapper
        self._col_arr = col_arr

    def _col_idxs_meta(self, col_idxs):
        """Get metadata of column indices.

        Returns element indices and new column array.
        Automatically decides whether to use column range or column map."""
        if self.is_sorted():
            new_indices, new_col_arr = nb.col_range_select_nb(self.col_range, to_1d(col_idxs))  # faster
        else:
            new_indices, new_col_arr = nb.col_map_select_nb(self.col_map, to_1d(col_idxs))
        return new_indices, new_col_arr

    @property
    def wrapper(self):
        """Array wrapper."""
        return self._wrapper

    @property
    def col_arr(self):
        """Column array."""
        return self._col_arr

    @cached_method
    def get_col_arr(self, group_by=None):
        """Get group-aware column array."""
        group_arr = self.wrapper.grouper.get_groups(group_by=group_by)
        if group_arr is not None:
            col_arr = group_arr[self.col_arr]
        else:
            col_arr = self.col_arr
        return col_arr

    @cached_property
    def col_range(self):
        """Column index.

        Faster than `ColumnMapper.col_map` but only compatible with sorted columns.
        More suited for records."""
        return nb.col_range_nb(self.col_arr, len(self.wrapper.columns))

    @cached_method
    def get_col_range(self, group_by=None):
        """Get group-aware column range."""
        if not self.wrapper.grouper.is_grouped(group_by=group_by):
            return self.col_range
        col_arr = self.get_col_arr(group_by=group_by)
        columns = self.wrapper.get_columns(group_by=group_by)
        return nb.col_range_nb(col_arr, len(columns))

    @cached_property
    def col_map(self):
        """Column map.

        More flexible than `ColumnMapper.col_range`.
        More suited for mapped arrays."""
        return nb.col_map_nb(self.col_arr, len(self.wrapper.columns))

    @cached_method
    def get_col_map(self, group_by=None):
        """Get group-aware column map."""
        if not self.wrapper.grouper.is_grouped(group_by=group_by):
            return self.col_map
        col_arr = self.get_col_arr(group_by=group_by)
        columns = self.wrapper.get_columns(group_by=group_by)
        return nb.col_map_nb(col_arr, len(columns))

    @cached_method
    def is_sorted(self):
        """Check whether column array is sorted."""
        return nb.is_col_sorted_nb(self.col_arr)


