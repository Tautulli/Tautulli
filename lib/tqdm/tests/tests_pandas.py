from nose.plugins.skip import SkipTest

from tqdm import tqdm
from tests_tqdm import with_setup, pretest, posttest, StringIO, closing


@with_setup(pretest, posttest)
def test_pandas_series():
    """Test pandas.Series.progress_apply and .progress_map"""
    try:
        from numpy.random import randint
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        tqdm.pandas(file=our_file, leave=True, ascii=True)

        series = pd.Series(randint(0, 50, (123,)))
        res1 = series.progress_apply(lambda x: x + 10)
        res2 = series.apply(lambda x: x + 10)
        assert res1.equals(res2)

        res3 = series.progress_map(lambda x: x + 10)
        res4 = series.map(lambda x: x + 10)
        assert res3.equals(res4)

        expects = ['100%', '123/123']
        for exres in expects:
            our_file.seek(0)
            if our_file.getvalue().count(exres) < 2:
                our_file.seek(0)
                raise AssertionError(
                    "\nExpected:\n{0}\nIn:\n{1}\n".format(
                        exres + " at least twice.", our_file.read()))


@with_setup(pretest, posttest)
def test_pandas_data_frame():
    """Test pandas.DataFrame.progress_apply and .progress_applymap"""
    try:
        from numpy.random import randint
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        tqdm.pandas(file=our_file, leave=True, ascii=True)
        df = pd.DataFrame(randint(0, 50, (100, 200)))

        def task_func(x):
            return x + 1

        # applymap
        res1 = df.progress_applymap(task_func)
        res2 = df.applymap(task_func)
        assert res1.equals(res2)

        # apply
        for axis in [0, 1]:
            res3 = df.progress_apply(task_func, axis=axis)
            res4 = df.apply(task_func, axis=axis)
            assert res3.equals(res4)

        our_file.seek(0)
        if our_file.read().count('100%') < 3:
            our_file.seek(0)
            raise AssertionError("\nExpected:\n{0}\nIn:\n{1}\n".format(
                '100% at least three times', our_file.read()))

        # apply_map, apply axis=0, apply axis=1
        expects = ['20000/20000', '200/200', '100/100']
        for exres in expects:
            our_file.seek(0)
            if our_file.getvalue().count(exres) < 1:
                our_file.seek(0)
                raise AssertionError(
                    "\nExpected:\n{0}\nIn:\n {1}\n".format(
                        exres + " at least once.", our_file.read()))


@with_setup(pretest, posttest)
def test_pandas_groupby_apply():
    """Test pandas.DataFrame.groupby(...).progress_apply"""
    try:
        from numpy.random import randint
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        tqdm.pandas(file=our_file, leave=False, ascii=True)

        df = pd.DataFrame(randint(0, 50, (500, 3)))
        df.groupby(0).progress_apply(lambda x: None)

        dfs = pd.DataFrame(randint(0, 50, (500, 3)), columns=list('abc'))
        dfs.groupby(['a']).progress_apply(lambda x: None)

        our_file.seek(0)

        # don't expect final output since no `leave` and
        # high dynamic `miniters`
        nexres = '100%|##########|'
        if nexres in our_file.read():
            our_file.seek(0)
            raise AssertionError("\nDid not expect:\n{0}\nIn:{1}\n".format(
                nexres, our_file.read()))

    with closing(StringIO()) as our_file:
        tqdm.pandas(file=our_file, leave=True, ascii=True)

        dfs = pd.DataFrame(randint(0, 50, (500, 3)), columns=list('abc'))
        dfs.loc[0] = [2, 1, 1]
        dfs['d'] = 100

        expects = ['500/500', '1/1', '4/4', '2/2']
        dfs.groupby(dfs.index).progress_apply(lambda x: None)
        dfs.groupby('d').progress_apply(lambda x: None)
        dfs.groupby(dfs.columns, axis=1).progress_apply(lambda x: None)
        dfs.groupby([2, 2, 1, 1], axis=1).progress_apply(lambda x: None)

        our_file.seek(0)
        if our_file.read().count('100%') < 4:
            our_file.seek(0)
            raise AssertionError("\nExpected:\n{0}\nIn:\n{1}\n".format(
                '100% at least four times', our_file.read()))

        for exres in expects:
            our_file.seek(0)
            if our_file.getvalue().count(exres) < 1:
                our_file.seek(0)
                raise AssertionError(
                    "\nExpected:\n{0}\nIn:\n {1}\n".format(
                        exres + " at least once.", our_file.read()))


@with_setup(pretest, posttest)
def test_pandas_leave():
    """Test pandas with `leave=True`"""
    try:
        from numpy.random import randint
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        df = pd.DataFrame(randint(0, 100, (1000, 6)))
        tqdm.pandas(file=our_file, leave=True, ascii=True)
        df.groupby(0).progress_apply(lambda x: None)

        our_file.seek(0)

        exres = '100%|##########| 100/100'
        if exres not in our_file.read():
            our_file.seek(0)
            raise AssertionError(
                "\nExpected:\n{0}\nIn:{1}\n".format(exres, our_file.read()))


@with_setup(pretest, posttest)
def test_pandas_apply_args_deprecation():
    """Test warning info in
    `pandas.Dataframe(Series).progress_apply(func, *args)`"""
    try:
        from numpy.random import randint
        from tqdm import tqdm_pandas
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        tqdm_pandas(tqdm(file=our_file, leave=False, ascii=True, ncols=20))
        df = pd.DataFrame(randint(0, 50, (500, 3)))
        df.progress_apply(lambda x: None, 1)  # 1 shall cause a warning
        # Check deprecation message
        res = our_file.getvalue()
        assert all([i in res for i in (
            "TqdmDeprecationWarning", "not supported",
            "keyword arguments instead")])


@with_setup(pretest, posttest)
def test_pandas_deprecation():
    """Test bar object instance as argument deprecation"""
    try:
        from numpy.random import randint
        from tqdm import tqdm_pandas
        import pandas as pd
    except ImportError:
        raise SkipTest

    with closing(StringIO()) as our_file:
        tqdm_pandas(tqdm(file=our_file, leave=False, ascii=True, ncols=20))
        df = pd.DataFrame(randint(0, 50, (500, 3)))
        df.groupby(0).progress_apply(lambda x: None)
        # Check deprecation message
        assert "TqdmDeprecationWarning" in our_file.getvalue()
        assert "instead of `tqdm_pandas(tqdm(...))`" in our_file.getvalue()

    with closing(StringIO()) as our_file:
        tqdm_pandas(tqdm, file=our_file, leave=False, ascii=True, ncols=20)
        df = pd.DataFrame(randint(0, 50, (500, 3)))
        df.groupby(0).progress_apply(lambda x: None)
        # Check deprecation message
        assert "TqdmDeprecationWarning" in our_file.getvalue()
        assert "instead of `tqdm_pandas(tqdm, ...)`" in our_file.getvalue()
