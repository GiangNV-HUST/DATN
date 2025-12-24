/**
 * Alert List Component
 * Hiển thị danh sách alerts
 */
import React from 'react';
import {
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Typography,
  Box,
  Divider,
} from '@mui/material';
import {
  Warning,
  TrendingUp,
  TrendingDown,
  ShowChart,
  VolumeUp,
  Info,
} from '@mui/icons-material';
import { formatDateTime } from '../utils/formatters';

// Icon map cho alert types
const alertIcons = {
  rsi_overbought: { icon: <Warning />, color: '#ff1744' },
  rsi_oversold: { icon: <Warning />, color: '#00c853' },
  golden_cross: { icon: <TrendingUp />, color: '#00c853' },
  death_cross: { icon: <TrendingDown />, color: '#ff1744' },
  volume_spike: { icon: <VolumeUp />, color: '#ff9800' },
  default: { icon: <Info />, color: '#1976d2' },
};

// Severity colors
const severityColors = {
  critical: 'error',
  warning: 'warning',
  info: 'info',
};

const AlertList = ({ alerts, maxItems = 10 }) => {
  if (!alerts || alerts.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có cảnh báo</Typography>
      </Paper>
    );
  }

  const displayAlerts = alerts.slice(0, maxItems);

  return (
    <Paper>
      <Box p={2}>
        <Typography variant="h6">
          🔔 Cảnh báo gần đây
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {alerts.length} cảnh báo
        </Typography>
      </Box>
      
      <Divider />

      <List>
        {displayAlerts.map((alert, index) => {
          const alertIcon = alertIcons[alert.alert_type] || alertIcons.default;
          const severity = alert.alert_level || 'info';

          return (
            <React.Fragment key={alert.id || index}>
              <ListItem>
                <ListItemIcon>
                  <Box
                    sx={{
                      color: alertIcon.color,
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    {alertIcon.icon}
                  </Box>
                </ListItemIcon>

                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body1" fontWeight="bold">
                        {alert.ticker}
                      </Typography>
                      <Chip
                        label={severity}
                        size="small"
                        color={severityColors[severity] || 'default'}
                      />
                    </Box>
                  }
                  secondary={
                    <React.Fragment>
                      <Typography variant="body2" component="span">
                        {alert.message}
                      </Typography>
                      <br />
                      <Typography variant="caption" color="text.secondary">
                        {formatDateTime(alert.created_at || alert.create_at)}
                      </Typography>
                    </React.Fragment>
                  }
                />
              </ListItem>
              {index < displayAlerts.length - 1 && <Divider />}
            </React.Fragment>
          );
        })}
      </List>
    </Paper>
  );
};

export default AlertList;