/**
 * Prediction Chart Component
 * Hiển thị giá thực tế + dự đoán 3 ngày tới
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
} from 'recharts';
import { Paper, Typography, Box, Chip, Alert } from '@mui/material';
import { formatCurrency, formatDate } from '../utils/formatters';
import { TrendingUp } from '@mui/icons-material';

const PredictionChart = ({ 
  historicalData, 
  predictions, 
  ticker 
}) => {
  if (!historicalData || historicalData.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dữ liệu lịch sử</Typography>
      </Paper>
    );
  }

  if (!predictions || !predictions.predictions) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">Không có dự đoán</Typography>
      </Paper>
    );
  }

  // Lấy 10 ngày gần nhất
  const recentHistory = [...historicalData]
    .reverse()
    .slice(-10)
    .map(d => ({
      date: d.time,
      actual: d.close,
      type: 'actual'
    }));

  // Tạo prediction data
  const lastDate = new Date(recentHistory[recentHistory.length - 1].date);
  const predictionData = predictions.predictions.map((price, index) => {
    const date = new Date(lastDate);
    date.setDate(date.getDate() + index + 1);
    return {
      date: date.toISOString(),
      predicted: price,
      type: 'predicted'
    };
  });

  // Combine data
  const chartData = [
    ...recentHistory,
    {
      date: lastDate.toISOString(),
      actual: recentHistory[recentHistory.length - 1].actual,
      predicted: predictions.predictions[0], // Điểm nối
      type: 'junction'
    },
    ...predictionData
  ];

  // Tính % thay đổi dự đoán
  const lastPrice = recentHistory[recentHistory.length - 1].actual;
  const predictedPrice = predictions.predictions[predictions.predictions.length - 1];
  const changePercent = ((predictedPrice - lastPrice) / lastPrice) * 100;

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h6">
            🔮 Dự đoán giá 3 ngày tới
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Dựa trên Moving Average
          </Typography>
        </Box>
        
        {/* Change Chip */}
        <Chip
          icon={<TrendingUp />}
          label={`${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`}
          color={changePercent >= 0 ? 'success' : 'error'}
          sx={{ fontWeight: 'bold' }}
        />
      </Box>

      {/* Alert */}
      <Alert severity="info" sx={{ mb: 2 }}>
        ⚠️ Dự đoán chỉ mang tính chất tham khảo, không phải khuyến nghị đầu tư
      </Alert>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={350}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
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

          {/* Vertical line tại điểm dự đoán */}
          <ReferenceLine
            x={lastDate.toISOString()}
            stroke="#ff9800"
            strokeDasharray="3 3"
            label={{ value: 'Dự đoán từ đây', position: 'top' }}
          />

          {/* Actual Price Line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#1976d2"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="Giá thực tế"
            connectNulls={false}
          />

          {/* Predicted Price Line */}
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#ff9800"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={{ r: 4, fill: '#ff9800' }}
            name="Dự đoán"
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Prediction Details */}
      <Box mt={3}>
        <Typography variant="subtitle2" gutterBottom>
          Chi tiết dự đoán:
        </Typography>
        <Box display="flex" gap={2} flexWrap="wrap">
          {predictions.predictions.map((price, index) => {
            const date = new Date(lastDate);
            date.setDate(date.getDate() + index + 1);
            
            return (
              <Paper key={index} sx={{ p: 2, minWidth: 150 }} elevation={2}>
                <Typography variant="body2" color="text.secondary">
                  Ngày {index + 1} ({date.getDate()}/{date.getMonth() + 1})
                </Typography>
                <Typography variant="h6" color="primary">
                  {formatCurrency(price)}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    color: price > lastPrice ? '#00c853' : '#ff1744',
                    fontWeight: 'bold'
                  }}
                >
                  {price > lastPrice ? '↑' : '↓'} {(((price - lastPrice) / lastPrice) * 100).toFixed(2)}%
                </Typography>
              </Paper>
            );
          })}
        </Box>
      </Box>
    </Paper>
  );
};

export default PredictionChart;