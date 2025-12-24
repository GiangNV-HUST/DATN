/**
 * Stock Detail Page
 * Hiển thị chi tiết cổ phiếu + Indicators + Predictions + Alerts
 */
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  CircularProgress,
  Typography,
  Button,
  ButtonGroup,
} from '@mui/material';

import StockSummary from '../components/StockSummary';
import StockChart from '../components/StockChart';
import IndicatorsDashboard from '../components/IndicatorsDashboard';
import PredictionChart from '../components/PredictionChart';
import AlertList from '../components/AlertList';
import {
  getStockSummary,
  getStockHistory,
  getPredictions,
  getAlertByTicker,
} from '../services/api';

const StockDetail = () => {
  const { ticker } = useParams();
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Load summary
        const summaryData = await getStockSummary(ticker);
        setSummary(summaryData);

        // Load history
        const historyData = await getStockHistory(ticker, days);
        setHistory(historyData.data || []);

        // Load predictions
        try {
          const predData = await getPredictions(ticker);
          if (predData && predData.predictions && predData.predictions['3day']) {
            setPredictions(predData.predictions['3day']);
          }
        } catch (error) {
          console.log('No predictions available');
        }

        // Load alerts
        try {
          const alertsData = await getAlertByTicker(ticker, 20);
          setAlerts(alertsData.alerts || []);
        } catch (error) {
          console.log('No alerts available');
        }

      } catch (error) {
        console.error('Error loading stock detail:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ticker, days]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Chi tiết: {ticker}
        </Typography>

        {/* Time Range Buttons */}
        <ButtonGroup variant="outlined">
          <Button
            variant={days === 7 ? 'contained' : 'outlined'}
            onClick={() => setDays(7)}
          >
            7D
          </Button>
          <Button
            variant={days === 30 ? 'contained' : 'outlined'}
            onClick={() => setDays(30)}
          >
            30D
          </Button>
          <Button
            variant={days === 90 ? 'contained' : 'outlined'}
            onClick={() => setDays(90)}
          >
            90D
          </Button>
          <Button
            variant={days === 180 ? 'contained' : 'outlined'}
            onClick={() => setDays(180)}
          >
            6M
          </Button>
          <Button
            variant={days === 365 ? 'contained' : 'outlined'}
            onClick={() => setDays(365)}
          >
            1Y
          </Button>
        </ButtonGroup>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Summary */}
        <StockSummary data={summary} />

        {/* Chart */}
        <StockChart
          data={history}
          title={`Biểu đồ giá ${ticker} - ${days} ngày`}
          showVolume={true}
        />

        {/* Indicators Dashboard */}
        <Box>
          <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
            📊 Chỉ báo kỹ thuật
          </Typography>
          <IndicatorsDashboard data={history} />
        </Box>

        {/* Predictions */}
        <Box>
          <PredictionChart
            historicalData={history}
            predictions={predictions}
            ticker={ticker}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default StockDetail;