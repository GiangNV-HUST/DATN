/**
 * Alerts Page
 * Hiển thị tất cả alerts
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
} from '@mui/material';

import AlertList from '../components/AlertList';
import { getAlerts } from '../services/api';

const AlertsPage = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterLevel, setFilterLevel] = useState('all');

  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const data = await getAlerts(null, 100);
        setAlerts(data.alerts || []);
      } catch (error) {
        console.error('Error loading alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  // Filter alerts
  const filteredAlerts = filterLevel === 'all'
    ? alerts
    : alerts.filter(a => a.alert_level === filterLevel);

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          🔔 Cảnh báo
        </Typography>

        {/* Filter */}
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Mức độ</InputLabel>
          <Select
            value={filterLevel}
            label="Mức độ"
            onChange={(e) => setFilterLevel(e.target.value)}
          >
            <MenuItem value="all">Tất cả</MenuItem>
            <MenuItem value="critical">Critical</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="info">Info</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Stats */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6">
          Tổng số: {filteredAlerts.length} cảnh báo
        </Typography>
      </Paper>

      {/* Alert List */}
      <AlertList alerts={filteredAlerts} maxItems={50} />
    </Box>
  );
};

export default AlertsPage;
