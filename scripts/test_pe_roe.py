# -*- coding: utf-8 -*-
"""Test script to check PE/ROE data availability from VnStock"""
import warnings
warnings.filterwarnings('ignore')
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from vnstock import Vnstock

def test_pe_roe():
    """Test PE/ROE data from VnStock API with proper MultiIndex handling"""
    tickers = ['VCB', 'FPT', 'VNM']

    for ticker in tickers:
        print(f"\n{'='*50}")
        print(f"Testing {ticker}")
        print('='*50)

        try:
            stock = Vnstock().stock(symbol=ticker, source='VCI')

            # Test finance ratio
            print("\n1. Finance Ratio (with MultiIndex fix):")
            ratio_data = stock.finance.ratio(period='quarter', lang='en')
            if ratio_data is not None and not ratio_data.empty:
                # Flatten MultiIndex columns if present
                if isinstance(ratio_data.columns, pd.MultiIndex):
                    latest = ratio_data.iloc[-1]
                    ratio_dict = {}
                    for col in ratio_data.columns:
                        if isinstance(col, tuple):
                            metric_name = col[1]
                            ratio_dict[metric_name] = latest[col]
                        else:
                            ratio_dict[col] = latest[col]
                else:
                    ratio_dict = ratio_data.iloc[-1].to_dict()

                # Extract values using actual column names
                pe_val = ratio_dict.get('P/E') or ratio_dict.get('PE')
                pb_val = ratio_dict.get('P/B') or ratio_dict.get('PB')
                roe_val = ratio_dict.get('ROE (%)') or ratio_dict.get('ROE')
                eps_val = ratio_dict.get('EPS (VND)') or ratio_dict.get('EPS')

                print(f"   P/E: {pe_val}")
                print(f"   P/B: {pb_val}")
                print(f"   ROE (%): {roe_val}")
                print(f"   EPS (VND): {eps_val}")
            else:
                print("   No ratio data")

        except Exception as e:
            print(f"   Error: {e}")

if __name__ == '__main__':
    test_pe_roe()
