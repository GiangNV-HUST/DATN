/**
 * Moving Average Chart Component
 * Hiển thị giá đóng cửa + các đường MA
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
} from 'recharts';
import { Paper, Typography, Box, Chip } from '@mui/material';
import { formatCurrency, formatDate } from '../utils/formatters';

const MAChart = ({ data, title = 'Moving Averages' }) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu</Typography>
      </Paper>
    );
  }

  // Đảo ngược data
  const chartData = [...data].reverse();

  // Kiểm tra có MA nào không
  const hasMA5 = chartData.some(d => d.ma5);
  const hasMA10 = chartData.some(d => d.ma10);
  const hasMA20 = chartData.some(d => d.ma20);
  const hasMA50 = chartData.some(d => d.ma50);
  const hasMA100 = chartData.some(d => d.ma100);

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">{title}</Typography>
        
        {/* MA Legend Chips */}
        <Box display="flex" gap={1}>
          {hasMA5 && <Chip label="MA5" size="small" sx={{ backgroundColor: '#ff6b6b', color: 'white' }} />}
          {hasMA10 && <Chip label="MA10" size="small" sx={{ backgroundColor: '#4ecdc4', color: 'white' }} />}
          {hasMA20 && <Chip label="MA20" size="small" sx={{ backgroundColor: '#45b7d1', color: 'white' }} />}
          {hasMA50 && <Chip label="MA50" size="small" sx={{ backgroundColor: '#96ceb4', color: 'white' }} />}
          {hasMA100 && <Chip label="MA100" size="small" sx={{ backgroundColor: '#ffeaa7', color: '#2d3436' }} />}
        </Box>
      </Box>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
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

          {/* Close Price */}
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2d3436"
            strokeWidth={2}
            dot={false}
            name="Giá"
          />

          {/* MA Lines */}
          {hasMA5 && (
            <Line
              type="monotone"
              dataKey="ma5"
              stroke="#ff6b6b"
              strokeWidth={1.5}
              dot={false}
              name="MA5"
            />
          )}
          {hasMA10 && (
            <Line
              type="monotone"
              dataKey="ma10"
              stroke="#4ecdc4"
              strokeWidth={1.5}
              dot={false}
              name="MA10"
            />
          )}
          {hasMA20 && (
            <Line
              type="monotone"
              dataKey="ma20"
              stroke="#45b7d1"
              strokeWidth={1.5}
              dot={false}
              name="MA20"
            />
          )}
          {hasMA50 && (
            <Line
              type="monotone"
              dataKey="ma50"
              stroke="#96ceb4"
              strokeWidth={1.5}
              dot={false}
              name="MA50"
            />
          )}
          {hasMA100 && (
            <Line
              type="monotone"
              dataKey="ma100"
              stroke="#fdcb6e"
              strokeWidth={1.5}
              dot={false}
              name="MA100"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default MAChart;