/**
 * Stock Summary Component
 * Hiển thị tóm tắt thông tin cổ phiếu
 */
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
} from '@mui/icons-material';
import {
  formatCurrency,
  formatPercent,
  formatVolume,
  formatDateTime,
  getPriceColor,
  getRSILevel,
} from '../utils/formatters';

const StockSummary = ({ data }) => {
  if (!data) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">Không có dữ liệu</Typography>
        </CardContent>
      </Card>
    );
  }

  const {
    ticker,
    latest_price,
    change_percent,
    rsi,
    volume,
    last_updated,
  } = data;

  const priceColor = getPriceColor(change_percent || 0);
  const rsiLevel = rsi ? getRSILevel(rsi) : null;

  // Icon cho trend
  const TrendIcon = change_percent > 0 
    ? TrendingUp 
    : change_percent < 0 
    ? TrendingDown 
    : TrendingFlat;

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h4" component="div">
            {ticker}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <TrendIcon style={{ color: priceColor }} />
            <Typography
              variant="h5"
              style={{ color: priceColor }}
            >
              {formatPercent(change_percent || 0)}
            </Typography>
          </Box>
        </Box>

        {/* Price */}
        <Typography variant="h3" gutterBottom>
          {formatCurrency(latest_price)}
        </Typography>

        {/* Indicators */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mt: 2 }}>
          {/* RSI */}
          {rsi !== null && rsi !== undefined && (
            <Box sx={{ minWidth: '150px', flex: '1 1 auto' }}>
              <Typography variant="body2" color="text.secondary">
                RSI
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h6">
                  {rsi.toFixed(2)}
                </Typography>
                {rsiLevel && (
                  <Chip
                    label={rsiLevel.text}
                    size="small"
                    sx={{
                      backgroundColor: rsiLevel.color,
                      color: 'white',
                      fontSize: '0.7rem',
                    }}
                  />
                )}
              </Box>
            </Box>
          )}

          {/* Volume */}
          {volume && (
            <Box sx={{ minWidth: '150px', flex: '1 1 auto' }}>
              <Typography variant="body2" color="text.secondary">
                Volume
              </Typography>
              <Typography variant="h6">
                {formatVolume(volume)}
              </Typography>
            </Box>
          )}

          {/* Last Updated */}
          <Box sx={{ minWidth: '150px', flex: '1 1 auto' }}>
            <Typography variant="body2" color="text.secondary">
              Cập nhật
            </Typography>
            <Typography variant="body1">
              {formatDateTime(last_updated)}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default StockSummary;