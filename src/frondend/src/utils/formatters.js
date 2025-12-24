/**
 * Utility functions cho formatting
 */

/**
 * Format thành VNĐ
 */
export const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("vi-VN");
};

/**
 * Format datetime
 */
export const formatDateTime = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("vi-VN");
};

/**
 * Format volume
 */
export const formatVolume = (value) => {
  if (!value) return "0";

  if (value >= 1000000) {
    return (value / 1000000).toFixed(2) + "M";
  } else if (value >= 1000) {
    return (value / 1000).toFixed(2) + "K";
  }
  return value.toString();
};

/**
 * Format Currency (VND)
 */
export const formatCurrency = (value) => {
  if (!value && value !== 0) return "N/A";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(value);
};

/**
 * Format percent
 */
export const formatPercent = (value) => {
  if (!value && value !== 0) return "0.00%";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
};

/**
 * Get color cho giá (tăng/giảm)
 */
export const getPriceColor = (changePercent) => {
  if (changePercent > 0) return "#00c853";
  if (changePercent < 0) return "#ff1744";
  return "#ffc107";
};

/**
 * Get RSI level
 */
export const getRSILevel = (rsi) => {
  if (rsi >= 70) return { text: "Overbought", color: "#ff1744" };
  if (rsi <= 30) return { text: "Oversold", color: "#00c853" };
  return { text: "Neutral", color: "#ffc107" };
};
