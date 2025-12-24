/**
 * Stock Chart Component
 * Hiển thị biểu đồ giá cổ phiếu với Line Chart
 */

import React from "react";
import {
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Paper, Typography, Box } from "@mui/material";
import { formatCurrency, formatDate, formatVolume } from "../utils/formatters";

/**
 * Custom Tooltip
 */
const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;

    return (
      <Paper sx={{ p: 1.5, maxWidth: 250 }}>
        <Typography variant="subtitle2" gutterBottom>
          {formatDate(data.time)}
        </Typography>
        <Box sx={{ fontSize: "0.875rem" }}>
          <Box display="flex" justifyContent="space-between">
            <span>Open:</span>
            <strong>{formatCurrency(data.open)}</strong>
          </Box>
          <Box display="flex" justifyContent="space-between">
            <span>High:</span>
            <strong style={{ color: "#00c853" }}>
              {formatCurrency(data.high)}
            </strong>
          </Box>
          <Box display="flex" justifyContent="space-between">
            <span>Low:</span>
            <strong style={{ color: "#ff1744" }}>
              {formatCurrency(data.low)}
            </strong>
          </Box>
          <Box display="flex" justifyContent="space-between">
            <span>Close:</span>
            <strong>{formatCurrency(data.close)}</strong>
          </Box>
          {data.volume && (
            <Box display="flex" justifyContent="space-between" mt={1}>
              <span>Volume:</span>
              <strong>{formatVolume(data.volume)}</strong>
            </Box>
          )}
        </Box>
      </Paper>
    );
  }
  return null;
};

/**
 * Main StockChart Component
 */
const StockChart = ({ data, title, showVolume = true }) => {
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: "center" }}>
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

      {/* Price Chart - Using Line Chart instead of Candlestick */}
      <Box sx={{ mb: 2 }}>
        <ResponsiveContainer width="100%" height={380}>
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
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
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {/* Area for close price */}
            <Area
              type="monotone"
              dataKey="close"
              fill="#8884d8"
              fillOpacity={0.3}
              stroke="#8884d8"
              strokeWidth={2}
              name="Close Price"
            />

            {/* Lines for High and Low */}
            <Line
              type="monotone"
              dataKey="high"
              stroke="#00c853"
              strokeWidth={1}
              dot={false}
              name="High"
            />
            <Line
              type="monotone"
              dataKey="low"
              stroke="#ff1744"
              strokeWidth={1}
              dot={false}
              name="Low"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Box>

      {/* Volume Chart */}
      {showVolume && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Volume
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getDate()}/${date.getMonth() + 1}`;
                }}
              />
              <YAxis tickFormatter={(value) => formatVolume(value)} />
              <Tooltip
                formatter={(value) => formatVolume(value)}
                labelFormatter={(label) => formatDate(label)}
              />
              <Bar dataKey="volume" fill="#42a5f5" name="Volume" />
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Paper>
  );
};

export default StockChart;
