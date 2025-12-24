/**
 * MACD Chart Component
 * Hiển thị MACD, Signal Line, và Histogram
 */
import React from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Paper, Typography } from '@mui/material';
import { formatDate } from '../utils/formatters';

const MACDChart = ({ data, title = 'MACD - Moving Average Convergence Divergence' }) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu</Typography>
      </Paper>
    );
  }

  // Đảo ngược data và filter chỉ lấy có MACD
  const chartData = [...data]
    .reverse()
    .filter(d => d.macd_main !== null && d.macd_main !== undefined);

  if (chartData.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu MACD</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      <ResponsiveContainer width="100%" height={250}>
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
          <YAxis />
          <Tooltip
            formatter={(value) => value?.toFixed(2) || 'N/A'}
            labelFormatter={(label) => formatDate(label)}
          />
          <Legend />

          {/* Zero Line */}
          <ReferenceLine y={0} stroke="#888" strokeDasharray="3 3" />

          {/* Histogram (MACD - Signal) */}
          <Bar
            dataKey="macd_diff"
            fill="#42a5f5"
            name="Histogram"
            opacity={0.6}
          />

          {/* MACD Line */}
          <Line
            type="monotone"
            dataKey="macd_main"
            stroke="#1976d2"
            strokeWidth={2}
            dot={false}
            name="MACD"
          />

          {/* Signal Line */}
          <Line
            type="monotone"
            dataKey="macd_signal"
            stroke="#ff6b6b"
            strokeWidth={2}
            dot={false}
            name="Signal"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default MACDChart;