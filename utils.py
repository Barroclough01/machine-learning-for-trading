#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions for machine learning in trading applications.
This module provides helper functions for time formatting and cross-validation
specifically designed for financial time series data.
"""

__author__ = "Stefan Jansen"

import numpy as np

# Set random seed for reproducibility
np.random.seed(42)


def format_time(t):
    """
    Convert a numeric time value into a formatted string.

    Args:
        t (float): Time value in seconds

    Returns:
        str: Formatted time string in 'HH:MM:SS' format

    Example:
        >>> format_time(3661)
        '01:01:01'
    """
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    return f"{h:0>2.0f}:{m:0>2.0f}:{s:0>2.0f}"


class MultipleTimeSeriesCV:
    """
    Time series cross-validation for multiple assets.

    This class implements a custom cross-validation strategy specifically designed
    for financial time series data with multiple assets. It handles the unique
    challenges of financial data including:
    - Multiple assets (symbols) with different dates
    - Avoiding look-ahead bias by purging overlapping outcomes
    - Maintaining temporal order of data

    The class assumes the input data has a MultiIndex with 'symbol' and 'date' levels.

    Attributes:
        n_splits (int): Number of cross-validation splits
        train_period_length (int): Length of training period in days
        test_period_length (int): Length of test period in days
        lookahead (int): Number of days to look ahead (for purging)
        date_idx (str): Name of the date index level
        shuffle (bool): Whether to shuffle training data
    """

    def __init__(
        self,
        n_splits=3,
        train_period_length=126,  # ~6 months of trading days
        test_period_length=21,  # ~1 month of trading days
        lookahead=None,
        date_idx="date",
        shuffle=False,
    ):
        """
        Initialize the cross-validation strategy.

        Args:
            n_splits (int): Number of cross-validation splits
            train_period_length (int): Length of training period in days
            test_period_length (int): Length of test period in days
            lookahead (int): Number of days to look ahead for purging
            date_idx (str): Name of the date index level
            shuffle (bool): Whether to shuffle training data
        """
        self.n_splits = n_splits
        self.lookahead = lookahead
        self.test_length = test_period_length
        self.train_length = train_period_length
        self.shuffle = shuffle
        self.date_idx = date_idx

    def split(self, X, y=None, groups=None):
        """
        Generate train/test indices for cross-validation.

        Args:
            X (pd.DataFrame): Input features with MultiIndex (symbol, date)
            y (pd.Series, optional): Target variable
            groups (None): Not used, present for sklearn compatibility

        Yields:
            tuple: (train_idx, test_idx) pairs of indices for each split
        """
        # Get unique dates and sort in reverse order (newest first)
        unique_dates = X.index.get_level_values(self.date_idx).unique()
        days = sorted(unique_dates, reverse=True)
        split_idx = []

        # Calculate split indices for each fold
        for i in range(self.n_splits):
            test_end_idx = i * self.test_length
            test_start_idx = test_end_idx + self.test_length
            train_end_idx = test_start_idx + self.lookahead - 1
            train_start_idx = train_end_idx + self.train_length + self.lookahead - 1
            split_idx.append(
                [train_start_idx, train_end_idx, test_start_idx, test_end_idx]
            )

        # Get date index for filtering
        dates = X.reset_index()[[self.date_idx]]

        # Generate train/test splits
        for train_start, train_end, test_start, test_end in split_idx:
            # Get training indices
            train_idx = dates[
                (dates[self.date_idx] > days[train_start])
                & (dates[self.date_idx] <= days[train_end])
            ].index
            # Get test indices
            test_idx = dates[
                (dates[self.date_idx] > days[test_start])
                & (dates[self.date_idx] <= days[test_end])
            ].index
            # Optionally shuffle training data
            if self.shuffle:
                np.random.shuffle(list(train_idx))
            yield train_idx.to_numpy(), test_idx.to_numpy()

    def get_n_splits(self, X, y, groups=None):
        """
        Get the number of cross-validation splits.

        Args:
            X (pd.DataFrame): Input features
            y (pd.Series, optional): Target variable
            groups (None): Not used, present for sklearn compatibility

        Returns:
            int: Number of splits
        """
        return self.n_splits
