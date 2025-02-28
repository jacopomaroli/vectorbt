import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytest

import vectorbt as vbt
from vectorbt.utils.config import merge_dicts

seed = 42


# ############# base.py ############# #


class MyData(vbt.Data):
    @classmethod
    def download_symbol(cls, symbol, shape=(5, 3), start_date=datetime(2020, 1, 1), columns=None, index_mask=None,
                        column_mask=None, return_arr=False, tz_localize=None, seed=seed):
        np.random.seed(seed)
        a = np.random.uniform(size=shape) + symbol
        if return_arr:
            return a
        index = [start_date + timedelta(days=i) for i in range(a.shape[0])]
        if a.ndim == 1:
            sr = pd.Series(a, index=index, name=columns)
            if index_mask is not None:
                sr = sr.loc[index_mask]
            if tz_localize is not None:
                sr = sr.tz_localize(tz_localize)
            return sr
        df = pd.DataFrame(a, index=index, columns=columns)
        if index_mask is not None:
            df = df.loc[index_mask]
        if column_mask is not None:
            df = df.loc[:, column_mask]
        if tz_localize is not None:
            df = df.tz_localize(tz_localize)
        return df

    def update_symbol(self, symbol, n=1, **kwargs):
        download_kwargs = self.select_symbol_kwargs(symbol, self.download_kwargs)
        download_kwargs['start_date'] = self.data[symbol].index[-1]
        shape = download_kwargs.pop('shape', (5, 3))
        new_shape = (n, shape[1]) if len(shape) > 1 else (n,)
        new_seed = download_kwargs.pop('seed', seed) + 1
        kwargs = merge_dicts(download_kwargs, kwargs)
        return self.download_symbol(symbol, shape=new_shape, seed=new_seed, **kwargs)


class TestData:
    def test_config(self, tmp_path):
        data = MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2'])
        assert MyData.loads(data.dumps()) == data
        data.save(tmp_path / 'data')
        assert MyData.load(tmp_path / 'data') == data

    def test_download(self):
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), return_arr=True).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ]
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3), return_arr=True).data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.8324426408004217, 0.21233911067827616, 0.18182496720710062]
                ]
            )
        )
        index = pd.DatetimeIndex(
            ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05'],
            dtype='datetime64[ns]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,)).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), columns='feat0').data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index,
                name='feat0'
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3)).data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.8324426408004217, 0.21233911067827616, 0.18182496720710062]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.8324426408004217, 0.21233911067827616, 0.18182496720710062]
                ],
                index=index,
                columns=pd.Index(['feat0', 'feat1', 'feat2'], dtype='object'))
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,)).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,)).data[1],
            pd.Series(
                [
                    1.3745401188473625,
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366,
                    1.15601864044243652
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3)).data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.8324426408004217, 0.21233911067827616, 0.18182496720710062]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3)).data[1],
            pd.DataFrame(
                [
                    [1.3745401188473625, 1.9507143064099162, 1.7319939418114051],
                    [1.5986584841970366, 1.15601864044243652, 1.15599452033620265],
                    [1.05808361216819946, 1.8661761457749352, 1.6011150117432088],
                    [1.7080725777960455, 1.020584494295802447, 1.9699098521619943],
                    [1.8324426408004217, 1.21233911067827616, 1.18182496720710062]
                ],
                index=index
            )
        )
        tzaware_index = pd.DatetimeIndex(
            [
                '2020-01-01 01:00:00',
                '2020-01-02 01:00:00',
                '2020-01-03 01:00:00',
                '2020-01-04 01:00:00',
                '2020-01-05 01:00:00'
            ],
            dtype='datetime64[ns, Europe/Berlin]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), tz_localize='UTC', tz_convert='Europe/Berlin').data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=tzaware_index
            )
        )
        index_mask = vbt.symbol_dict({
            0: [False, True, True, True, True],
            1: [True, True, True, True, False]
        })
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan').data[0],
            pd.Series(
                [
                    np.nan,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan').data[1],
            pd.Series(
                [
                    1.3745401188473625,
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366,
                    np.nan
                ],
                index=index
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop').data[0],
            pd.Series(
                [
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366
                ],
                index=index[1:4]
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop').data[1],
            pd.Series(
                [
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366
                ],
                index=index[1:4]
            )
        )
        column_mask = vbt.symbol_dict({
            0: [False, True, True],
            1: [True, True, False]
        })
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan').data[0],
            pd.DataFrame(
                [
                    [np.nan, np.nan, np.nan],
                    [np.nan, 0.15601864044243652, 0.15599452033620265],
                    [np.nan, 0.8661761457749352, 0.6011150117432088],
                    [np.nan, 0.020584494295802447, 0.9699098521619943],
                    [np.nan, 0.21233911067827616, 0.18182496720710062]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan').data[1],
            pd.DataFrame(
                [
                    [1.3745401188473625, 1.9507143064099162, np.nan],
                    [1.5986584841970366, 1.15601864044243652, np.nan],
                    [1.05808361216819946, 1.8661761457749352, np.nan],
                    [1.7080725777960455, 1.020584494295802447, np.nan],
                    [np.nan, np.nan, np.nan]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop').data[0],
            pd.DataFrame(
                [
                    [0.15601864044243652],
                    [0.8661761457749352],
                    [0.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop').data[1],
            pd.DataFrame(
                [
                    [1.15601864044243652],
                    [1.8661761457749352],
                    [1.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )
        with pytest.raises(Exception) as e_info:
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='raise', missing_columns='nan')
        with pytest.raises(Exception) as e_info:
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='raise')
        with pytest.raises(Exception) as e_info:
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='test', missing_columns='nan')
        with pytest.raises(Exception) as e_info:
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='test')

    def test_update(self):
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), return_arr=True).update().data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896
                ]
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), return_arr=True).update(n=2).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896,
                    0.6090665392794814
                ]
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3), return_arr=True).update().data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.11505456638977896, 0.6090665392794814, 0.13339096418598828]
                ]
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3), return_arr=True).update(n=2).data[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.11505456638977896, 0.6090665392794814, 0.13339096418598828],
                    [0.24058961996534878, 0.3271390558111398, 0.8591374909485977]
                ]
            )
        )
        index = pd.DatetimeIndex(
            ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05'],
            dtype='datetime64[ns]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,)).update().data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896
                ],
                index=index
            )
        )
        index2 = pd.DatetimeIndex(
            ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05', '2020-01-06'],
            dtype='datetime64[ns]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,)).update(n=2).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896,
                    0.6090665392794814
                ],
                index=index2
            )
        )
        tzaware_index = pd.DatetimeIndex(
            [
                '2020-01-01 01:00:00',
                '2020-01-02 01:00:00',
                '2020-01-03 01:00:00',
                '2020-01-04 01:00:00',
                '2020-01-05 01:00:00'
            ],
            dtype='datetime64[ns, Europe/Berlin]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), tz_localize='UTC', tz_convert='Europe/Berlin')
                .update(tz_localize=None).data[0],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896
                ],
                index=tzaware_index
            )
        )
        index_mask = vbt.symbol_dict({
            0: [False, True, True, True, True],
            1: [True, True, True, True, False]
        })
        update_index_mask = vbt.symbol_dict({
            0: [True],
            1: [False]
        })
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan')
                .update(index_mask=update_index_mask).data[0],
            pd.Series(
                [
                    np.nan,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896
                ],
                index=index
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan')
                .update(index_mask=update_index_mask).data[1],
            pd.Series(
                [
                    1.3745401188473625,
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366,
                    np.nan
                ],
                index=index
            )
        )
        update_index_mask2 = vbt.symbol_dict({
            0: [True, False],
            1: [False, True]
        })
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan')
                .update(n=2, index_mask=update_index_mask2).data[0],
            pd.Series(
                [
                    np.nan,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.11505456638977896,
                    np.nan
                ],
                index=index2
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='nan')
                .update(n=2, index_mask=update_index_mask2).data[1],
            pd.Series(
                [
                    1.3745401188473625,
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366,
                    np.nan,
                    1.6090665392794814
                ],
                index=index2
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop')
                .update(index_mask=update_index_mask).data[0],
            pd.Series(
                [
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366
                ],
                index=index[1:4]
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop')
                .update(index_mask=update_index_mask).data[1],
            pd.Series(
                [
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366
                ],
                index=index[1:4]
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop')
                .update(n=2, index_mask=update_index_mask2).data[0],
            pd.Series(
                [
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366
                ],
                index=index[1:4]
            )
        )
        pd.testing.assert_series_equal(
            MyData.download([0, 1], shape=(5,), index_mask=index_mask, missing_index='drop')
                .update(n=2, index_mask=update_index_mask2).data[1],
            pd.Series(
                [
                    1.9507143064099162,
                    1.7319939418114051,
                    1.5986584841970366
                ],
                index=index[1:4]
            )
        )
        column_mask = vbt.symbol_dict({
            0: [False, True, True],
            1: [True, True, False]
        })
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan')
                .update(index_mask=update_index_mask).data[0],
            pd.DataFrame(
                [
                    [np.nan, np.nan, np.nan],
                    [np.nan, 0.15601864044243652, 0.15599452033620265],
                    [np.nan, 0.8661761457749352, 0.6011150117432088],
                    [np.nan, 0.020584494295802447, 0.9699098521619943],
                    [np.nan, 0.6090665392794814, 0.13339096418598828]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan')
                .update(index_mask=update_index_mask).data[1],
            pd.DataFrame(
                [
                    [1.3745401188473625, 1.9507143064099162, np.nan],
                    [1.5986584841970366, 1.15601864044243652, np.nan],
                    [1.05808361216819946, 1.8661761457749352, np.nan],
                    [1.7080725777960455, 1.020584494295802447, np.nan],
                    [np.nan, np.nan, np.nan]
                ],
                index=index
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan')
                .update(n=2, index_mask=update_index_mask2).data[0],
            pd.DataFrame(
                [
                    [np.nan, np.nan, np.nan],
                    [np.nan, 0.15601864044243652, 0.15599452033620265],
                    [np.nan, 0.8661761457749352, 0.6011150117432088],
                    [np.nan, 0.020584494295802447, 0.9699098521619943],
                    [np.nan, 0.6090665392794814, 0.13339096418598828],
                    [np.nan, np.nan, np.nan]
                ],
                index=index2
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='nan', missing_columns='nan')
                .update(n=2, index_mask=update_index_mask2).data[1],
            pd.DataFrame(
                [
                    [1.3745401188473625, 1.9507143064099162, np.nan],
                    [1.5986584841970366, 1.15601864044243652, np.nan],
                    [1.05808361216819946, 1.8661761457749352, np.nan],
                    [1.7080725777960455, 1.020584494295802447, np.nan],
                    [np.nan, np.nan, np.nan],
                    [1.2405896199653488, 1.3271390558111398, np.nan]
                ],
                index=index2
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop')
                .update(index_mask=update_index_mask).data[0],
            pd.DataFrame(
                [
                    [0.15601864044243652],
                    [0.8661761457749352],
                    [0.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop')
                .update(index_mask=update_index_mask).data[1],
            pd.DataFrame(
                [
                    [1.15601864044243652],
                    [1.8661761457749352],
                    [1.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop')
                .update(n=2, index_mask=update_index_mask2).data[0],
            pd.DataFrame(
                [
                    [0.15601864044243652],
                    [0.8661761457749352],
                    [0.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), index_mask=index_mask, column_mask=column_mask,
                            missing_index='drop', missing_columns='drop')
                .update(n=2, index_mask=update_index_mask2).data[1],
            pd.DataFrame(
                [
                    [1.15601864044243652],
                    [1.8661761457749352],
                    [1.020584494295802447]
                ],
                index=index[1:4],
                columns=pd.Int64Index([1], dtype='int64')
            )
        )

    def test_concat(self):
        index = pd.DatetimeIndex(
            ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05'],
            dtype='datetime64[ns]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), columns='feat0').concat()['feat0'],
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index,
                name=0
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5,), columns='feat0').concat()['feat0'],
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.9507143064099162, 1.9507143064099162],
                    [0.7319939418114051, 1.7319939418114051],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.15601864044243652, 1.15601864044243652]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat0'],
            pd.Series(
                [
                    0.3745401188473625,
                    0.5986584841970366,
                    0.05808361216819946,
                    0.7080725777960455,
                    0.8324426408004217
                ],
                index=index,
                name=0
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat1'],
            pd.Series(
                [
                    0.9507143064099162,
                    0.15601864044243652,
                    0.8661761457749352,
                    0.020584494295802447,
                    0.21233911067827616
                ],
                index=index,
                name=0
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat2'],
            pd.Series(
                [
                    0.7319939418114051,
                    0.15599452033620265,
                    0.6011150117432088,
                    0.9699098521619943,
                    0.18182496720710062
                ],
                index=index,
                name=0
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat0'],
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.05808361216819946, 1.05808361216819946],
                    [0.7080725777960455, 1.7080725777960455],
                    [0.8324426408004217, 1.8324426408004217]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat1'],
            pd.DataFrame(
                [
                    [0.9507143064099162, 1.9507143064099162],
                    [0.15601864044243652, 1.15601864044243652],
                    [0.8661761457749352, 1.8661761457749352],
                    [0.020584494295802447, 1.020584494295802447],
                    [0.21233911067827616, 1.21233911067827616]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).concat()['feat2'],
            pd.DataFrame(
                [
                    [0.7319939418114051, 1.7319939418114051],
                    [0.15599452033620265, 1.15599452033620265],
                    [0.6011150117432088, 1.6011150117432088],
                    [0.9699098521619943, 1.9699098521619943],
                    [0.18182496720710062, 1.18182496720710062]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )

    def test_get(self):
        index = pd.DatetimeIndex(
            ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05'],
            dtype='datetime64[ns]',
            freq='D'
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5,), columns='feat0').get(),
            pd.Series(
                [
                    0.3745401188473625,
                    0.9507143064099162,
                    0.7319939418114051,
                    0.5986584841970366,
                    0.15601864044243652
                ],
                index=index,
                name='feat0'
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).get(),
            pd.DataFrame(
                [
                    [0.3745401188473625, 0.9507143064099162, 0.7319939418114051],
                    [0.5986584841970366, 0.15601864044243652, 0.15599452033620265],
                    [0.05808361216819946, 0.8661761457749352, 0.6011150117432088],
                    [0.7080725777960455, 0.020584494295802447, 0.9699098521619943],
                    [0.8324426408004217, 0.21233911067827616, 0.18182496720710062]
                ],
                index=index,
                columns=pd.Index(['feat0', 'feat1', 'feat2'], dtype='object')
            )
        )
        pd.testing.assert_series_equal(
            MyData.download(0, shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).get('feat0'),
            pd.Series(
                [
                    0.3745401188473625,
                    0.5986584841970366,
                    0.05808361216819946,
                    0.7080725777960455,
                    0.8324426408004217
                ],
                index=index,
                name='feat0'
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5,), columns='feat0').get(),
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.9507143064099162, 1.9507143064099162],
                    [0.7319939418114051, 1.7319939418114051],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.15601864044243652, 1.15601864044243652]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).get('feat0'),
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.05808361216819946, 1.05808361216819946],
                    [0.7080725777960455, 1.7080725777960455],
                    [0.8324426408004217, 1.8324426408004217]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).get(['feat0', 'feat1'])[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.05808361216819946, 1.05808361216819946],
                    [0.7080725777960455, 1.7080725777960455],
                    [0.8324426408004217, 1.8324426408004217]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )
        pd.testing.assert_frame_equal(
            MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).get()[0],
            pd.DataFrame(
                [
                    [0.3745401188473625, 1.3745401188473625],
                    [0.5986584841970366, 1.5986584841970366],
                    [0.05808361216819946, 1.05808361216819946],
                    [0.7080725777960455, 1.7080725777960455],
                    [0.8324426408004217, 1.8324426408004217]
                ],
                index=index,
                columns=pd.Int64Index([0, 1], dtype='int64', name='symbol')
            )
        )

    def test_indexing(self):
        assert MyData.download([0, 1], shape=(5,), columns='feat0').iloc[:3].wrapper == \
               MyData.download([0, 1], shape=(3,), columns='feat0').wrapper
        assert MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2']).iloc[:3].wrapper == \
               MyData.download([0, 1], shape=(3, 3), columns=['feat0', 'feat1', 'feat2']).wrapper
        assert MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2'])['feat0'].wrapper == \
               MyData.download([0, 1], shape=(5,), columns='feat0').wrapper
        assert MyData.download([0, 1], shape=(5, 3), columns=['feat0', 'feat1', 'feat2'])[['feat0']].wrapper == \
               MyData.download([0, 1], shape=(5, 1), columns=['feat0']).wrapper


# ############# updater.py ############# #

class TestDataUpdater:
    def test_update(self):
        data = MyData.download(0, shape=(5,), return_arr=True)
        updater = vbt.DataUpdater(data)
        updater.update()
        assert updater.data == data.update()
        assert updater.config['data'] == data.update()

    def test_update_every(self):
        data = MyData.download(0, shape=(5,), return_arr=True)
        kwargs = dict(call_count=0)

        class DataUpdater(vbt.DataUpdater):
            def update(self, kwargs):
                super().update()
                kwargs['call_count'] += 1
                if kwargs['call_count'] == 5:
                    raise vbt.CancelledError

        updater = DataUpdater(data)
        updater.update_every(kwargs=kwargs)
        for i in range(5):
            data = data.update()
        assert updater.data == data
        assert updater.config['data'] == data
