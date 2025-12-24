/**
 * Simple Line Chart Component
 * Hiển thị biểu đồ đường đơn giản
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
import { Paper, Typography } from '@mui/material';
import { formatCurrency, formatDate } from '../utils/formatters';

const SimpleLineChart = ({ 
  data, 
  title, 
  dataKey = 'close',
  lineColor = '#1976d2',
  height = 300 
}) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu</Typography>
      </Paper>
    );
  }

  // Đảo ngược data để hiển thị từ cũ đến mới
  const chartData = [...data].reverse();

  return (
    <Paper sx={{ p: 2 }}>
      {title && (
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
      )}

      <ResponsiveContainer width="100%" height={height}>
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
            tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value) => formatCurrency(value)}
            labelFormatter={(label) => formatDate(label)}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            name="Giá"
          />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default SimpleLineChart;