/**
 * Indicators Dashboard Component
 * Tổng hợp tất cả indicators
 */
import React from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import MAChart from './MAChart';
import RSIChart from './RSIChart';
import MACDChart from './MACDChart';
import BollingerChart from './BollingerChart';

const IndicatorsDashboard = ({ data }) => {
  const [tabValue, setTabValue] = React.useState(0);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  if (!data || data.length === 0) {
    return (
      <Box p={3} textAlign="center">
        <Typography color="text.secondary">Không có dữ liệu indicators</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Tabs */}
      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="Moving Averages" />
        <Tab label="RSI" />
        <Tab label="MACD" />
        <Tab label="Bollinger Bands" />
      </Tabs>

      {/* Tab Panels */}
      {tabValue === 0 && (
        <Box>
          <MAChart data={data} />
        </Box>
      )}

      {tabValue === 1 && (
        <Box>
          <RSIChart data={data} />
        </Box>
      )}

      {tabValue === 2 && (
        <Box>
          <MACDChart data={data} />
        </Box>
      )}

      {tabValue === 3 && (
        <Box>
          <BollingerChart data={data} />
        </Box>
      )}
    </Box>
  );
};

export default IndicatorsDashboard;