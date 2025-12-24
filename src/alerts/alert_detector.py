import pandas as pd
import logging

logger = logging.getLogger(__name__)


class AlertDetector:
    def __init__(self):
        pass

    def detect_all_alerts(self, df):
        if df is None or df.empty:
            return []

        alerts = []
        latest = df.iloc[-1]
        ticker = latest.get('ticker', 'UNKNOWN')

        alerts.extend(self._detect_rsi_alerts(ticker, latest))

        if len(df) >= 2:
            alerts.extend(self._detect_ma_cross_alerts(ticker, df))

        if len(df) >= 20:
            alerts.extend(self._detect_volume_alerts(ticker, df))

        if len(df) >= 2:
            alerts.extend(self._detect_macd_alerts(ticker, df))

        logger.info(f"Detected {len(alerts)} alerts")
        return alerts

    def _detect_rsi_alerts(self, ticker, latest):
        alerts = []
        rsi = latest.get('rsi')

        if pd.isna(rsi):
            return alerts

        if rsi > 70:
            severity = "HIGH" if rsi > 80 else "WARNING"
            alerts.append({
                'ticker': ticker,
                'type': 'RSI_OVERBOUGHT',
                'severity': severity,
                'message': f'{ticker} RSI = {rsi:.1f} (Overbought)',
                'value': {'rsi': rsi},
                'price': latest.get('close')
            })

        elif rsi < 30:
            severity = "HIGH" if rsi < 20 else "WARNING"
            alerts.append({
                'ticker': ticker,
                'type': 'RSI_OVERSOLD',
                'severity': severity,
                'message': f'{ticker} RSI = {rsi:.1f} (Oversold)',
                'value': {'rsi': rsi},
                'price': latest.get('close')
            })

        return alerts

    def _detect_ma_cross_alerts(self, ticker, df):
        alerts = []

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        ma5_curr = latest.get('ma5')
        ma20_curr = latest.get('ma20')
        ma5_prev = previous.get('ma5')
        ma20_prev = previous.get('ma20')

        if pd.isna(ma5_curr) or pd.isna(ma20_curr) or pd.isna(ma5_prev) or pd.isna(ma20_prev):
            return alerts

        if ma5_prev < ma20_prev and ma5_curr > ma20_curr:
            alerts.append({
                'ticker': ticker,
                'type': 'GOLDEN_CROSS',
                'severity': 'HIGH',
                'message': f'{ticker} Golden Cross - MA5 cat len MA20',
                'value': {'ma5': ma5_curr, 'ma20': ma20_curr},
                'price': latest.get('close')
            })

        elif ma5_prev > ma20_prev and ma5_curr < ma20_curr:
            alerts.append({
                'ticker': ticker,
                'type': 'DEATH_CROSS',
                'severity': 'WARNING',
                'message': f'{ticker} Death Cross - MA5 cat xuong MA20',
                'value': {'ma5': ma5_curr, 'ma20': ma20_curr},
                'price': latest.get('close')
            })

        return alerts

    def _detect_volume_alerts(self, ticker, df):
        alerts = []

        latest = df.iloc[-1]
        current_volume = latest.get('volume')

        if pd.isna(current_volume):
            return alerts

        recent_volumes = df.iloc[-21:-1]['volume'].dropna()
        if len(recent_volumes) == 0:
            return alerts

        avg_volume = recent_volumes.mean()

        if current_volume > avg_volume * 2:
            percent_increase = ((current_volume - avg_volume) / avg_volume) * 100
            alerts.append({
                'ticker': ticker,
                'type': 'VOLUME_SPIKE',
                'severity': 'INFO',
                'message': f'{ticker} Volume spike! 2.1x trung binh (+{percent_increase:.0f}%)',
                'value': {'current_volume': current_volume, 'avg_volume': avg_volume},
                'price': latest.get('close')
            })

        return alerts

    def _detect_macd_alerts(self, ticker, df):
        alerts = []

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        macd_curr = latest.get('macd_main')
        signal_curr = latest.get('macd_signal')
        macd_prev = previous.get('macd_main')
        signal_prev = previous.get('macd_signal')

        if pd.isna(macd_curr) or pd.isna(signal_curr) or pd.isna(macd_prev) or pd.isna(signal_prev):
            return alerts

        if macd_prev < signal_prev and macd_curr > signal_curr:
            alerts.append({
                'ticker': ticker,
                'type': 'MACD_BULLISH',
                'severity': 'INFO',
                'message': f'{ticker} MACD Bullish - MACD cat len Signal',
                'value': {'macd': macd_curr, 'signal': signal_curr},
                'price': latest.get('close')
            })

        elif macd_prev > signal_prev and macd_curr < signal_curr:
            alerts.append({
                'ticker': ticker,
                'type': 'MACD_BEARISH',
                'severity': 'WARNING',
                'message': f'{ticker} MACD Bearish - MACD cat xuong Signal',
                'value': {'macd': macd_curr, 'signal': signal_curr},
                'price': latest.get('close')
            })

        return alerts
