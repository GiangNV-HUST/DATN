/**
 * Main App component
 */
import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import StockDetail from "./pages/StockDetail";
import ScreenerPage from "./pages/ScreenerPage";
import AlertsPage from "./pages/AlertsPage";

// Tạo theme
const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1976d2",
    },
    secondary: {
      main: "#dc004e",
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="stock/:ticker" element={<StockDetail />} />
            <Route path="screener" element={<ScreenerPage />} />
            <Route path="alerts" element={<AlertsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
