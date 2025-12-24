/**
 * RSI Chart Component
 * Hiển thị Relative Strength Index
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
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import { Paper, Typography } from '@mui/material';
import { formatDate } from '../utils/formatters';

const RSIChart = ({ data, title = 'RSI - Relative Strength Index' }) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu</Typography>
      </Paper>
    );
  }

  // Đảo ngược data và filter chỉ lấy có RSI
  const chartData = [...data]
    .reverse()
    .filter(d => d.rsi !== null && d.rsi !== undefined);

  if (chartData.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu RSI</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart
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
          <YAxis domain={[0, 100]} />
          <Tooltip
            formatter={(value) => value.toFixed(2)}
            labelFormatter={(label) => formatDate(label)}
          />
          <Legend />

          {/* Overbought Zone (> 70) */}
          <ReferenceArea
            y1={70}
            y2={100}
            fill="#ff1744"
            fillOpacity={0.1}
            label={{ value: 'Overbought', position: 'top' }}
          />

          {/* Oversold Zone (< 30) */}
          <ReferenceArea
            y1={0}
            y2={30}
            fill="#00c853"
            fillOpacity={0.1}
            label={{ value: 'Oversold', position: 'bottom' }}
          />

          {/* Reference Lines */}
          <ReferenceLine y={70} stroke="#ff1744" strokeDasharray="3 3" />
          <ReferenceLine y={50} stroke="#888" strokeDasharray="3 3" />
          <ReferenceLine y={30} stroke="#00c853" strokeDasharray="3 3" />

          {/* RSI Line */}
          <Line
            type="monotone"
            dataKey="rsi"
            stroke="#1976d2"
            strokeWidth={2}
            dot={false}
            name="RSI"
          />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default RSIChart;