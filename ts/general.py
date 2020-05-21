"""Module dedicated to general time-series meta-features."""
import typing as t

import sklearn.preprocessing
import numpy as np
import scipy.spatial
import scipy.odr
import pandas as pd
import scipy.signal

import autocorr
import _detrend
import _embed
import _period
import _utils
import _get_data


class MFETSGeneral:
    """Extract time-series meta-features from General group."""
    @staticmethod
    def _calc_season_mode_ind(ts_season: np.ndarray, ts_period: int,
                              indfunc: t.Callable[[np.ndarray], float]) -> int:
        """Calculate a mode index based on the time-series seasonality.

        Used by both ``ft_trough_frac`` and ``ft_peak_frac`` to calculate,
        respectively, the mode of the argmin and argmax for all seasons.
        """
        inds = np.arange(ts_period)

        inds = np.array([
            indfunc(ts_season[i * ts_period + inds])
            for i in np.arange(1, ts_season.size // ts_period)
        ],
                        dtype=int)

        mode_inds, _ = scipy.stats.mode(inds)
        return mode_inds[0] + 1

    @classmethod
    def _ts_walker(
            cls,
            ts: np.ndarray,
            step_size: float = 0.1,
            start_point: t.Optional[t.Union[int, float]] = None) -> np.ndarray:
        """Simulate a particle attracted to the current time-series value."""
        if start_point is None:
            # Note: actually, it is used mean(ts) as starting point. However,
            # we are using ts_scaled and, therefore, mean(ts_scaled) = 0.
            start_point = 0.0

        walker_path = np.zeros(ts.size, dtype=float)
        walker_path[0] = start_point

        for i in np.arange(1, ts.size):
            diff = ts[i - 1] - walker_path[i - 1]
            # Note: weighted average between the current time-series value
            # (with 'step_size' weight) and the previous particle position
            # (with '1 - step_size' weight).
            walker_path[i] = walker_path[i - 1] + step_size * diff

        return walker_path

    @classmethod
    def ft_length(cls, ts: np.ndarray) -> int:
        """Length of the time-series.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        Returns
        -------
        int
            Length of the time-seties.

        References
        ----------
        TODO.
        """
        return ts.size

    @classmethod
    def ft_diff(cls, ts: np.ndarray, order: int = 1) -> np.ndarray:
        """`n`th-order difference of the time-series.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        order : int, optional (default = 1)
            Order of differentiation.

        Returns
        -------
        :obj:`np.ndarray`
            `n`th-order differenced time-series values.
        """
        return np.diff(ts)

    @classmethod
    def ft_period(cls,
                  ts: np.ndarray,
                  ts_period: t.Optional[int] = None) -> int:
        """Period of the time-series.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        ts_period : int, optional (default = None)
            Time-series period. Used to take advantage of precomputations.

        Returns
        -------
        int
            Time-series period.
        """
        ts_period = _period.ts_period(ts=ts, ts_period=ts_period)
        return ts_period

    @classmethod
    def ft_turning_points(cls, ts: np.ndarray) -> np.ndarray:
        """Turning points in the time-series.

        A turning point is a time-series point `p_{i}` which both neighbor
        values, p_{i-1} and p_{i+1}, are either lower (p_{i} > p_{i+1} and
        p_{i} > p_{i-1}) or higher (p_{i} < p_{i+1} and p_{i} < p_{i-1}).

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        Returns
        -------
        :obj:`np.ndarray`
            Binary array marking (with `1`) where is the turning points in the
            time-series.

        References
        ----------
        TODO.
        """
        return _utils.find_crit_pt(ts, type_="non-plateau")

    @classmethod
    def ft_turning_points_trend(cls, ts_trend: np.ndarray) -> np.ndarray:
        """Turning points in the time-series trend.

        A turning point is a time-series point `p_{i}` which both neighbor
        values, p_{i-1} and p_{i+1}, are either lower (p_{i} > p_{i+1} and
        p_{i} > p_{i-1}) or higher (p_{i} < p_{i+1} and p_{i} < p_{i-1}).

        Parameters
        ----------
        ts_trend : :obj:`np.ndarray`
            One-dimensional time-series trend values.

        Returns
        -------
        :obj:`np.ndarray`
            Binary array marking where is the turning points in the
            time-series trend.

        References
        ----------
        TODO.
        """
        return cls.ft_turning_points(ts=ts_trend)

    @classmethod
    def ft_step_changes(cls, ts: np.ndarray, ddof: int = 1) -> np.ndarray:
        """Step change points in the time-series.

        Let p_{t_{a}}^{t_{b}} be the subsequence of observations from the
        timestep t_{a} and t_{b}, both inclusive. A point `p_i` is a
        step change if and only if:

        abs(p_{i} - mean(p_{1}^{i-1})) > 2 * std(p_{1}^{i-1})

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        ddof : float, optional (default = 1)
            Degrees of freedom for standard deviation.

        Returns
        -------
        :obj:`np.ndarray`
            Binary array marking where is the step change points in the
            time-series.

        References
        ----------
        TODO.
        """
        ts_cmeans = np.cumsum(ts) / np.arange(1, ts.size + 1)

        ts_mean_abs_div = np.abs(ts[1:] - ts_cmeans[:-1])

        step_changes = np.array([
            int(ts_mean_abs_div[i - 1] > 2 * np.std(ts[:i], ddof=ddof))
            for i in np.arange(1 + ddof, ts.size)
        ],
                                dtype=int)

        return step_changes

    @classmethod
    def ft_step_changes_trend(cls,
                              ts_trend: np.ndarray,
                              ddof: int = 1) -> np.ndarray:
        """Step change points in the time-series trend.

        Let p_{t_{a}}^{t_{b}} be the subsequence of observations from the
        timestep t_{a} and t_{b}, both inclusive. A point `p_i` is a
        step change if and only if:

        abs(p_{i} - mean(p_{1}^{i-1})) > 2 * std(p_{1}^{i-1})

        Parameters
        ----------
        ts_trend : :obj:`np.ndarray`
            One-dimensional time-series trend values.

        ddof : float, optional (default = 1)
            Degrees of freedom for standard deviation.

        Returns
        -------
        :obj:`np.ndarray`
            Binary array marking where is the step change points in the
            time-series trend.

        References
        ----------
        TODO.
        """
        step_changes = cls.ft_step_changes(ts=ts_trend, ddof=ddof)
        return step_changes

    @classmethod
    def ft_pred(cls,
                ts: np.ndarray,
                embed_dim: int = 2,
                std_range: t.Union[int, float] = 3,
                num_spacing: t.Union[int, float] = 4,
                metric: str = "minkowski",
                p: t.Union[int, float] = 2,
                ddof: int = 1,
                max_nlags: t.Optional[int] = None,
                lag: t.Optional[t.Union[int, str]] = None,
                ts_acfs: t.Optional[np.ndarray] = None,
                ts_ami: t.Optional[np.ndarray] = None,
                ts_scaled: t.Optional[np.ndarray] = None) -> float:
        """Signal predictability using delay vector variance method.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        embed_dim : int, optional (default = 2)
            Dimension of the time-series embedding.

        std_range : int or float, optional (default = 3)
            Number of standard deviations in range of the delay vector
            variance analysis (around the mean value).

        num_spacing : int, optional (default = 4)
            Controls how fine is the spacing between the analysed values
            within the analysed range. The greater this parameter is, the
            less is the spacing between the analysed values around the mean.

        metric : str, optional (default = "minkowski")
            Distance metric to measure the pairwise distance between embedded
            time-series instances. Check `scipy.spatial.distance.pdist`
            documentation to see the full list of available distance metrics.

        p : int or float, optional (default = 2)
            Power parameter to minkowski metric (used only if metric is
            "minkowski").

        ddof : int, optional (default = 1)
            Degrees of freedom to calculate the variance within this function.
            (standard deviation of pairwise distances of embedded time-seres
            and the variance of radius nearest neighbors from the definition
            of the implemented meta-feature. Check references for in-depth
            information.)

        max_nlags : int, (default = None)
            If ``lag`` is not a numeric value, than it will be estimated using
            either the time-series autocorrelation or mutual information
            function estimated up to this argument value.

        lag : int or str, (default = None)
            Lag of the time-series embedding. It must be a strictly positive
            value, None or a string in {`acf`, `acf-nonsig`, `ami`}. In the
            last two type of options, the lag is estimated within this method
            using the given strategy method (or, if None, it is used the
            strategy `acf-nonsig` by default) up to ``max_nlags``.
                1. `acf`: the lag corresponds to the first non-positive value
                    in the autocorrelation function.
                2. `acf-nonsig`: lag corresponds to the first non-significant
                    value in the autocorrelation function (absolute value below
                    the critical value of 1.96 / sqrt(ts.size)).
                3. `ami`: lag corresponds to the first local minimum of the
                    time-series automutual information function.

        ts_acfs : :obj:`np.ndarray`, (default = None)
            Array of time-series autocorrelation function (for distinct ordered
            lags). Used only if ``lag`` is either `acf`, `acf-nonsig` or None.
            If this argument is not given and the previous condiditon is meet,
            the autocorrelation function will be calculated inside this method
            up to ``max_nlags``.

        ts_ami : :obj:`np.ndarray`, (default = None)
            Array of time-series automutual information function (for distinct
            ordered lags). Used only if ``lag`` is `ami`. If not given and the
            previous condiditon is meet, the automutual information function
            will be calculated inside this method up to ``max_nlags``.

        ts_scaled : :obj:`np.ndarray`, (default = None)
            Standardized time-series values. Used to take advantage of
            precomputations.

        Returns
        -------
        :obj:`np.ndarray`
            Array of predictability estimation of the embedded time-series
            using delay vector variance method.

        References
        ----------
        .. [1] Mandic DP, Chambers JA. 2001. Recurrent neural networks for
            prediction: learning algorithms, architectures and stability.
            New York, NY: John Wiley & Sons, Ltd.
        .. [2] Gautama T, Mandic DP, Hulle MMV. 2004. The delay vector variance
            method for detecting determinism and nonlinearity in time series.
            Physica D 190, 167–176. 
        .. [3] Gautama T, Hulle MMV, Mandic DP. 2004. On the characterisation
            of the deterministic/stochastic and linear/nonlinear nature of time
            series. Technical Report DPM-04-05. Imperial College London.
        .. [4] Mandic DP, Chen M, Gautama T, Van Hulle MM, Constantinides A.
            2008. On the characterization of the deterministic/stochastic and
            linear/nonlinear nature of time series. Proc. R. Soc. A 464,
            1141–1160.
        .. [5] Jaksic V, Mandic DP, Ryan K, Basu B, Pakrashi V. A comprehensive
            study of the delay vector variance method for quantification of
            nonlinearity in dynamical systems. R Soc Open Sci. 2016;3(1):150493.
            Published 2016 Jan 6. doi:10.1098/rsos.150493
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)
        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               max_nlags=max_nlags,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami)

        ts_embed = _embed.embed_ts(ts_scaled, lag=lag, dim=embed_dim)

        dist_mat = scipy.spatial.distance.pdist(ts_embed, metric=metric, p=p)

        dist_mean = np.mean(dist_mat)
        dist_std = np.std(dist_mat, ddof=ddof)

        dist_mat = scipy.spatial.distance.squareform(dist_mat)

        # Note: prevents the instance itself be considered its own neighbor.
        dist_mat[np.diag_indices_from(dist_mat)] = np.inf

        var_sets = np.zeros(num_spacing, dtype=float)

        for i in np.arange(num_spacing):
            threshold = max(
                0.0, dist_mean + std_range * dist_std *
                (i * 2 / (num_spacing - 1) - 1))

            neighbors = dist_mat <= threshold

            for neigh_inds in neighbors:
                if np.sum(neigh_inds) > ddof:
                    var_sets[i] += np.var(ts_embed[neigh_inds, :], ddof=ddof)

        # Note: originally, this value is also normalize dy the time-series
        # variance but, as we are using the standardized time-series, its
        # variance is equal 1.
        var_sets /= num_spacing

        return var_sets

    @classmethod
    def ft_frac_cp(
            cls,
            ts: np.ndarray,
            threshold: t.Optional[t.Union[int, float]] = None,
            normalize: bool = True,
            ts_scaled: t.Optional[np.ndarray] = None) -> t.Union[int, float]:
        """Cross-points of a given horizontal line.

        This method calculates the fraction that the transition between
        two consecutive observations in the time-series crosses a horizontal
        line given by `y = threshold` over all possible crosses (i.e., if
        the time-series values alternate between higher and lower values
        relative to the given threhsold in all transitions).

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        threshold : int or float, optional (default = None)
            Threshold to define the horizontal line in the form y = threshold.
            If None, the threshold will default to the time-series median.

        normalize : bool, optional (defualt = True)
            If True, return the fraction of actual crosses over all possible
            crosses. If False, return the number of crosses.

        ts_scaled : :obj:`np.ndarray`, (default = None)
            Standardized time-series values. Used to take advantage of
            precomputations.

        Returns
        -------
        int or float
            If `normalize` is True, return the fraction of transition crosses
            over all possible crosses given a fixed time-series length and a
            threshold. If `normalize` is False, return the number of crosses.
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        if threshold is None:
            threshold = np.median(ts_scaled)

        higher_med = ts_scaled <= threshold
        num_cp = np.sum(np.logical_xor(higher_med[1:], higher_med[:-1]))

        if normalize:
            num_cp /= ts_scaled.size - 1

        return num_cp

    @classmethod
    def ft_binmean(cls, ts: np.ndarray) -> np.ndarray:
        """Check whether values are below or above the average value.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        Returns
        -------
        :obj:`np.ndarray`
            Binary array with the time-series length, marking with `1` 
            observations above or equal the mean value, and `0` otherwise.
        """
        return (ts >= np.mean(ts)).astype(int)

    @classmethod
    def ft_fs_len(cls,
                  ts: np.ndarray,
                  num_bins: int = 10,
                  strategy: str = "equal-width") -> np.ndarray:
        """Lenght of discretized time-series values plateaus.

        The time-series is discretized using a histogram with number of bins
        equal to `num_bins` bins and its cuts are calculated using a method
        defined by the `strategy` parameter.

        Parameters
        ----------
        ts : :obj:`np.ndarray`
            One-dimensional time-series values.

        num_bins : int, optional (default = 10)
            Number of bins to discretize the time-series values.

        strategy : str, optional (default = `equal-width`)
            Strategy used to define the histogram bins. Must be either
            `equal-width` (bins with equal with) or `equiprobable` (bins
            with the same amount of observations within).

        Returns
        -------
        :obj:`np.ndarray`
            Length of each plateau in the discretized time-series values.
        """
        ts_disc = _utils.discretize(ts=ts,
                                    num_bins=num_bins,
                                    strategy=strategy)

        i = 1
        counter = 1
        fs_len = []  # type: t.List[int]

        while i < ts.size:
            if not np.isclose(ts_disc[i], ts_disc[i - 1]):
                fs_len.append(counter)
                counter = 1

            else:
                counter += 1

            i += 1

        return np.asarray(fs_len, dtype=float)

    @classmethod
    def ft_peak_frac(cls,
                     ts_season: np.ndarray,
                     ts_period: t.Optional[t.Union[int, str]] = None,
                     normalize: bool = True) -> t.Union[int, float]:
        """Fraction of where the seasonal peak is localed within a period.

        This method returns the fraction (relative to the time-series period)
        of the mode of the peak localization within every complete period
        in the given time-series. For instance, if the peak tends to appear in
        the middle of a time-series complete period, this method will return
        `0.5`. If, in contrast, the peak tends to appear as the first period
        observation, this method returns `0.0`.

        If the time-series is not seasonal (i.e., the seasonal component is
        empty and its period is 1), then this method returns `np.nan`.

        Parameters
        ----------
        ts_season : :obj:`np.ndarray`
            One-dimensional time-series seasonal component values.

        ts_period : int, optional (default = None)
            Period of the time series. If None, the period will be estimated
            as the lag corresponding to the absolute maximum of the time-series
            autocorrelation function.

        normalize : bool, optional (default = True)
            If False, the result will be the mode index of the seasonal peak.

        Returns
        -------
        int or float
            If ``ts_period`` is less or equal than 1, return :obj:`np.nan`.
            If `normalize` is True, return the fraction of the seasonal peak
            mode index over the time-series period. If `normalize` is False,
            return the seasonal peak mode index.
        """
        ts_period = _period.ts_period(ts=ts_season, ts_period=ts_period)

        if ts_period <= 1:
            return np.nan

        ind_peak = cls._calc_season_mode_ind(ts_season=ts_season,
                                             ts_period=ts_period,
                                             indfunc=np.argmax)

        if normalize:
            ind_peak /= ts_period  # type: ignore

        return ind_peak

    @classmethod
    def ft_trough_frac(cls,
                       ts_season: np.ndarray,
                       ts_period: t.Optional[t.Union[int, str]] = None,
                       normalize: bool = True) -> t.Union[int, float]:
        """Fraction of where the seasonal trough is localed within a period.

        This method returns the fraction (relative to the time-series period)
        of the mode of the trough localization within every complete period
        in the given time-series. For instance, if the trough tends to appear in
        the middle of a time-series complete period, this method will return
        `0.5`. If, in contrast, the trough tends to appear as the first period
        observation, this method returns `0.0`.

        If the time-series is not seasonal (i.e., the seasonal component is
        empty and its period is 1), then this method returns `np.nan`.

        Parameters
        ----------
        ts_season : :obj:`np.ndarray`
            One-dimensional time-series seasonal component values.

        ts_period : int, optional (default = None)
            Period of the time series. If None, the period will be estimated
            as the lag corresponding to the absolute maximum of the time-series
            autocorrelation function.

        normalize : bool, optional (default = True)
            If False, the result will be the mode index of the seasonal trough.

        Returns
        -------
        int or float
            If ``ts_period`` is less or equal than 1, return :obj:`np.nan`.
            If `normalize` is True, return the fraction of the seasonal trough
            mode index over the time-series period. If `normalize` is False,
            return the seasonal trough mode index.
        """
        ts_period = _period.ts_period(ts=ts_season, ts_period=ts_period)

        if ts_period <= 1:
            return np.nan

        ind_trough = cls._calc_season_mode_ind(ts_season=ts_season,
                                               ts_period=ts_period,
                                               indfunc=np.argmin)

        if normalize:
            ind_trough /= ts_period  # type: ignore

        return ind_trough

    @classmethod
    def ft_walker_path(cls,
                       ts: np.ndarray,
                       step_size: float = 0.1,
                       start_point: t.Optional[t.Union[int, float]] = None,
                       relative_dist: bool = True,
                       walker_path: t.Optional[np.ndarray] = None,
                       ts_scaled: t.Optional[np.ndarray] = None) -> np.ndarray:
        """TODO."""
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        if walker_path is None:
            walker_path = cls._ts_walker(ts=ts_scaled,
                                         step_size=step_size,
                                         start_point=start_point)

        if relative_dist:
            return np.abs(walker_path - ts_scaled)

        return walker_path

    @classmethod
    def ft_walker_cross_frac(
            cls,
            ts: np.ndarray,
            step_size: float = 0.1,
            start_point: t.Optional[t.Union[int, float]] = None,
            normalize: bool = True,
            walker_path: t.Optional[np.ndarray] = None,
            ts_scaled: t.Optional[np.ndarray] = None) -> t.Union[int, float]:
        """TODO."""
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        if walker_path is None:
            walker_path = cls._ts_walker(ts=ts_scaled,
                                         step_size=step_size,
                                         start_point=start_point)

        cross_num = np.sum((walker_path[:-1] - ts_scaled[:-1]) *
                           (walker_path[1:] - ts_scaled[1:]) < 0)

        if normalize:
            cross_num /= walker_path.size - 1

        return cross_num

    @classmethod
    def ft_moving_threshold(cls,
                            ts: np.ndarray,
                            rate_absorption: float = 0.1,
                            rate_decay: float = 0.1,
                            ts_scaled: t.Optional[np.ndarray] = None,
                            relative: bool = False) -> np.ndarray:
        """TODO."""
        if not 0 < rate_decay < 1:
            raise ValueError("'rate_decay' must be in (0, 1) (got {})."
                             "".format(rate_decay))

        if not 0 < rate_absorption < 1:
            raise ValueError("'rate_absorption' must be in (0, 1) (got"
                             " {}).".format(rate_absorption))

        ts_scaled = np.abs(_utils.standardize_ts(ts=ts, ts_scaled=ts_scaled))

        # Note: threshold[0] = std(ts_scaled) = 1.0.
        threshold = np.ones(1 + ts.size, dtype=float)

        _ra = 1 + rate_absorption
        _rd = 1 - rate_decay

        for ind in np.arange(ts_scaled.size):
            if ts_scaled[ind] > threshold[ind]:
                # Absorb from the time series (absolute) values
                threshold[1 + ind] = _ra * ts_scaled[ind]
            else:
                # Decay the threshold
                threshold[1 + ind] = _rd * threshold[ind]

        if relative:
            # Note: ignore the first initial threshold
            return threshold[1:] - ts_scaled

        return threshold

    @classmethod
    def ft_embed_in_shell(
            cls,
            ts: np.ndarray,
            radii: t.Tuple[float, float] = (0.0, 1.0),
            embed_dim: int = 2,
            lag: t.Optional[t.Union[str, int]] = None,
            normalize: bool = True,
            max_nlags: t.Optional[int] = None,
            ts_acfs: t.Optional[np.ndarray] = None,
            ts_ami: t.Optional[np.ndarray] = None,
            ts_scaled: t.Optional[np.ndarray] = None) -> t.Union[int, float]:
        """TODO."""
        radius_inner, radius_outer = radii

        if radius_inner < 0:
            raise ValueError("Inner radius must be non-negative (got {})."
                             "".format(radius_inner))

        if radius_outer <= 0:
            raise ValueError("Outer radius must be positive (got {})."
                             "".format(radius_outer))

        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami,
                               max_nlags=max_nlags)

        # Note: embed is given by x(t) = [x(t), x(t-1), ..., x(t-m+1)]^T
        embed = _embed.embed_ts(ts_scaled, dim=embed_dim, lag=lag)

        # Note: here we supposed that every embed forms a zero-centered
        # hypersphere using the regular hypersphere equation:
        # sqrt(x_{i}^2 + x^{i-1}^2 + ... + x^{i-m+1}) = Radius
        embed_radius = np.linalg.norm(embed, ord=2, axis=1)

        # Note: we can check if every embed is in the same zero-centered
        # hypershell because all hyperspheres embeds are also zero-centered.
        in_shape_num = np.sum(
            np.logical_and(radius_inner <= embed_radius,
                           embed_radius <= radius_outer))

        if normalize:
            in_shape_num /= embed_radius.size

        return in_shape_num

    @classmethod
    def ft_force_potential(
            cls,
            ts: np.ndarray,
            potential: str = "sine",
            params: t.Optional[t.Tuple[float, float, float]] = None,
            start_point: t.Optional[t.Tuple[float, float]] = None,
            ts_scaled: t.Optional[np.ndarray] = None) -> np.ndarray:
        """TODO."""
        DEF_PARAM = dict(
            sine=((1, 1, 0.1), lambda x: np.sin(x / alpha) / alpha),
            dblwell=((2, 0.1, 0.1), lambda x: alpha**2 * x - x**3),
        )

        if potential not in DEF_PARAM:
            raise ValueError("'potential' must be in {} (got '{}')."
                             "".format(DEF_PARAM.keys(), potential))

        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        alpha, fric, dt = DEF_PARAM[potential][0] if params is None else params
        f_force = DEF_PARAM[potential][1]

        pos, vel = np.zeros((2, ts_scaled.size), dtype=float)

        # Note: it is actually used (mean(ts), 0.0) as default start
        # point, but mean(ts_scaled) = 0.
        pos[0], vel[0] = (0.0, 0.0) if start_point is None else start_point

        for t_prev in np.arange(ts_scaled.size - 1):
            aux = f_force(pos[t_prev]) + ts_scaled[t_prev] - fric * vel[t_prev]
            pos[t_prev + 1] = pos[t_prev] + dt * vel[t_prev] + dt**2 * aux
            vel[t_prev + 1] = vel[t_prev] + dt * aux

        if not np.isfinite(pos[-1]):
            raise ValueError("Potential trajectory diverged.")

        return pos

    @classmethod
    def ft_stick_angles(
            cls,
            ts: np.ndarray,
            ts_scaled: t.Optional[np.ndarray] = None) -> np.ndarray:
        """TODO."""
        def calc_angles(inds: np.ndarray) -> np.ndarray:
            """TODO."""
            return np.arctan(np.diff(ts_scaled[inds]) / np.diff(inds))

        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        aux = ts_scaled >= 0
        ts_ang_pos = calc_angles(inds=np.flatnonzero(aux))
        ts_ang_neg = calc_angles(inds=np.flatnonzero(~aux))

        angles = np.hstack((ts_ang_pos, ts_ang_neg))

        return angles

    @classmethod
    def ft_emb_dim_cao(cls,
                       ts: np.ndarray,
                       dims: t.Union[int, t.Sequence[int]] = 16,
                       lag: t.Optional[t.Union[str, int]] = None,
                       tol_threshold: float = 0.05,
                       max_nlags: t.Optional[int] = None,
                       ts_scaled: t.Optional[np.ndarray] = None,
                       ts_acfs: t.Optional[np.ndarray] = None,
                       ts_ami: t.Optional[np.ndarray] = None,
                       emb_dim_cao_e1: t.Optional[np.ndarray] = None) -> int:
        """TODO.

        References
        ----------
        .. [1] Liangyue Cao, Practical method for determining the minimum
            embedding dimension of a scalar time series, Physica D: Nonlinear
            Phenomena, Volume 110, Issues 1–2, 1997, Pages 43-50,
            ISSN 0167-2789, https://doi.org/10.1016/S0167-2789(97)00118-8.
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami,
                               max_nlags=max_nlags)

        if emb_dim_cao_e1 is None:
            emb_dim_cao_e1, _ = _embed.embed_dim_cao(ts=ts,
                                                     ts_scaled=ts_scaled,
                                                     dims=dims,
                                                     lag=lag)

        e1_abs_diff = np.abs(np.diff(emb_dim_cao_e1))

        first_max_ind = 0

        try:
            first_max_ind = np.flatnonzero(e1_abs_diff <= tol_threshold)[0]

        except IndexError:
            pass

        return first_max_ind + 1

    @classmethod
    def ft_cao_e1(cls,
                  ts: np.ndarray,
                  dims: t.Union[int, t.Sequence[int]] = 16,
                  lag: t.Optional[t.Union[str, int]] = None,
                  max_nlags: t.Optional[int] = None,
                  ts_scaled: t.Optional[np.ndarray] = None,
                  ts_acfs: t.Optional[np.ndarray] = None,
                  ts_ami: t.Optional[np.ndarray] = None,
                  emb_dim_cao_e1: t.Optional[np.ndarray] = None) -> int:
        """TODO.

        References
        ----------
        .. [1] Liangyue Cao, Practical method for determining the minimum
            embedding dimension of a scalar time series, Physica D: Nonlinear
            Phenomena, Volume 110, Issues 1–2, 1997, Pages 43-50,
            ISSN 0167-2789, https://doi.org/10.1016/S0167-2789(97)00118-8.
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami,
                               max_nlags=max_nlags)

        if emb_dim_cao_e1 is None:
            emb_dim_cao_e1, _ = _embed.embed_dim_cao(ts=ts,
                                                     ts_scaled=ts_scaled,
                                                     dims=dims,
                                                     lag=lag)

        return emb_dim_cao_e1

    @classmethod
    def ft_cao_e2(cls,
                  ts: np.ndarray,
                  dims: t.Union[int, t.Sequence[int]] = 16,
                  lag: t.Optional[t.Union[str, int]] = None,
                  max_nlags: t.Optional[int] = None,
                  ts_scaled: t.Optional[np.ndarray] = None,
                  ts_acfs: t.Optional[np.ndarray] = None,
                  ts_ami: t.Optional[np.ndarray] = None,
                  emb_dim_cao_e2: t.Optional[np.ndarray] = None) -> int:
        """TODO.

        References
        ----------
        .. [1] Liangyue Cao, Practical method for determining the minimum
            embedding dimension of a scalar time series, Physica D: Nonlinear
            Phenomena, Volume 110, Issues 1–2, 1997, Pages 43-50,
            ISSN 0167-2789, https://doi.org/10.1016/S0167-2789(97)00118-8.
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami,
                               max_nlags=max_nlags)

        if emb_dim_cao_e2 is None:
            _, emb_dim_cao_e2 = _embed.embed_dim_cao(ts=ts,
                                                     ts_scaled=ts_scaled,
                                                     dims=dims,
                                                     lag=lag)

        return emb_dim_cao_e2

    @classmethod
    def ft_fnn_prop(cls,
                    ts: np.ndarray,
                    dims: t.Union[int, t.Sequence[int]] = 16,
                    lag: t.Optional[t.Union[str, int]] = None,
                    max_nlags: t.Optional[int] = None,
                    ts_scaled: t.Optional[np.ndarray] = None,
                    ts_acfs: t.Optional[np.ndarray] = None,
                    ts_ami: t.Optional[np.ndarray] = None,
                    fnn_prop: t.Optional[np.ndarray] = None) -> int:
        """TODO.

        References
        ----------
        .. [1] Determining embedding dimension for phase-space reconstruction using
            a geometrical construction, Kennel, Matthew B. and Brown, Reggie and
            Abarbanel, Henry D. I., Phys. Rev. A, volume 45, 1992, American
            Physical Society.
        """
        ts_scaled = _utils.standardize_ts(ts=ts, ts_scaled=ts_scaled)

        lag = _embed.embed_lag(ts=ts_scaled,
                               lag=lag,
                               ts_acfs=ts_acfs,
                               ts_ami=ts_ami,
                               max_nlags=max_nlags)

        if fnn_prop is None:
            fnn_prop = _embed.embed_dim_fnn(ts=ts,
                                            ts_scaled=ts_scaled,
                                            dims=dims,
                                            lag=lag)

        return fnn_prop


def _test() -> None:
    import matplotlib.pyplot as plt
    ts = _get_data.load_data(3)

    ts_period = _period.ts_period(ts)
    ts_trend, ts_season, ts_residuals = _detrend.decompose(ts,
                                                           ts_period=ts_period)
    ts = ts.to_numpy()
    print("TS period:", ts_period)

    res = MFETSGeneral.ft_fs_len(ts, num_bins=2)
    print(res)

    res = MFETSGeneral.ft_fnn_prop(ts)
    print(res)

    res = MFETSGeneral.ft_embed_in_shell(ts)
    print(res)

    res = MFETSGeneral.ft_stick_angles(ts)
    print(res)

    res = MFETSGeneral.ft_force_potential(ts, potential="sine")
    print(res)

    res = MFETSGeneral.ft_walker_cross_frac(ts)
    print(res)

    res = MFETSGeneral.ft_walker_path(ts)
    print(res)

    res = MFETSGeneral.ft_pred(ts)
    print(res)

    res = MFETSGeneral.ft_moving_threshold(ts, relative=True)
    print(res)

    res = MFETSGeneral.ft_turning_points(ts)
    print(np.mean(res))

    res = MFETSGeneral.ft_step_changes(ts)
    print(np.mean(res))

    res = MFETSGeneral.ft_turning_points_trend(ts_trend)
    print(np.mean(res))

    res = MFETSGeneral.ft_step_changes_trend(ts_trend)
    print(np.mean(res))

    res = MFETSGeneral.ft_length(ts)
    print(res)

    res = MFETSGeneral.ft_frac_cp(ts)
    print(res)

    res = MFETSGeneral.ft_fs_len(ts)
    print(res)

    res = MFETSGeneral.ft_binmean(ts)
    print(res)

    res = MFETSGeneral.ft_period(ts)
    print(res)

    res = MFETSGeneral.ft_peak_frac(ts_season)
    print(res)

    res = MFETSGeneral.ft_trough_frac(ts_season)
    print(res)


if __name__ == "__main__":
    _test()
