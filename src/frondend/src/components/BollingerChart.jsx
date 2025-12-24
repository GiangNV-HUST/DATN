/**
 * Bollinger Bands Chart Component
 * Hiển thị giá + Bollinger Bands (upper, middle, lower)
 */
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import { Paper, Typography } from '@mui/material';
import { formatCurrency, formatDate } from '../utils/formatters';

const BollingerChart = ({ data, title = 'Bollinger Bands' }) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu</Typography>
      </Paper>
    );
  }

  // Đảo ngược data và filter chỉ lấy có BB
  const chartData = [...data]
    .reverse()
    .filter(d => d.bb_upper && d.bb_middle && d.bb_lower);

  if (chartData.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu Bollinger Bands</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getDate()}/${date.getMonth() + 1}`;
            }}
          />
          <YAxis
            domain={[(dataMin) => dataMin * 0.98, (dataMax) => dataMax * 1.02]}
            tickFormatter={(value) => {
              if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
              if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
              return value.toFixed(0);
            }}
          />
          <Tooltip
            formatter={(value) => formatCurrency(value)}
            labelFormatter={(label) => formatDate(label)}
          />
          <Legend />

          {/* Bollinger Bands */}
          <Line
            type="monotone"
            dataKey="bb_upper"
            stroke="#ff6b6b"
            strokeWidth={1}
            dot={false}
            name="Upper Band"
            strokeDasharray="5 5"
          />
          <Line
            type="monotone"
            dataKey="bb_middle"
            stroke="#95a5a6"
            strokeWidth={1}
            dot={false}
            name="Middle Band"
            strokeDasharray="3 3"
          />
          <Line
            type="monotone"
            dataKey="bb_lower"
            stroke="#00c853"
            strokeWidth={1}
            dot={false}
            name="Lower Band"
            strokeDasharray="5 5"
          />

          {/* Close Price */}
          <Line
            type="monotone"
            dataKey="close"
            stroke="#1976d2"
            strokeWidth={2}
            dot={false}
            name="Giá"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default BollingerChart;