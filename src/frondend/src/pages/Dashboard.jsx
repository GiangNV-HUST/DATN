/**
 * Dashboard page - trang chính
 */
import React from 'react';
import {
  Grid,
  Typography,
  Box,
} from '@mui/material';

import StockList from '../components/StockList';

const Dashboard = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        📊 Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stock List */}
        <Grid item xs={12}>
          <StockList />
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;