/**
 * Layout component - khung chính của app
 */
import React from "react";
import { Link, Outlet } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Button,
} from "@mui/material";
import {
  ShowChart,
  Dashboard,
  Notifications,
  Search,
} from "@mui/icons-material";

const Layout = () => {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {/*App Bar */}
      <AppBar position="static">
        <Toolbar>
          <ShowChart sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Stock Analysis Dashboard
          </Typography>

          {/* Navigation */}
          <Button
            color="inherit"
            component={Link}
            to="/"
            startIcon={<Dashboard />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            component={Link}
            to="/screener"
            startIcon={<Search />}
          >
            Screener
          </Button>
          <Button
            color="inherit"
            component={Link}
            to="/alerts"
            startIcon={<Notifications />}
          >
            Alerts
          </Button>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        <Outlet />
      </Container>

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: "auto",
          backgroundColor: (theme) =>
            theme.palette.mode === "light"
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            ©️ 2024 Stock Analysis System - Powered by VnStock & Gemini AI
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default Layout;