/**
 * Stock List Component
 * Hiển thị danh sách cổ phiếu dạng table
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  CircularProgress,
  Box,
  Typography,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search } from '@mui/icons-material';
import {
  formatCurrency,
  formatPercent,
  getPriceColor,
} from '../utils/formatters';
import { getAllStocks, getStockSummary } from '../services/api';

const StockList = () => {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [summaries, setSummaries] = useState({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Load danh sách tickers
        const data = await getAllStocks();
        const tickers = data.tickers || [];
        setStocks(tickers);

        // Load summary cho 20 cổ phiếu đầu tiên
        const summaryPromises = tickers.slice(0, 20).map(async (ticker) => {
          try {
            const summary = await getStockSummary(ticker);
            return { ticker, summary };
          } catch (error) {
            return { ticker, summary: null };
          }
        });

        const results = await Promise.all(summaryPromises);
        const summariesMap = {};
        results.forEach(({ ticker, summary }) => {
          summariesMap[ticker] = summary;
        });
        setSummaries(summariesMap);

      } catch (error) {
        console.error('Error loading stocks:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleRowClick = (ticker) => {
    navigate(`/stock/${ticker}`);
  };

  // Filter stocks
  const filteredStocks = stocks.filter((ticker) =>
    ticker.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper>
      {/* Search */}
      <Box p={2}>
        <TextField
          fullWidth
          placeholder="Tìm kiếm cổ phiếu..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Table */}
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Ticker</strong></TableCell>
              <TableCell align="right"><strong>Giá</strong></TableCell>
              <TableCell align="right"><strong>Thay đổi</strong></TableCell>
              <TableCell align="right"><strong>RSI</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredStocks
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((ticker) => {
                const summary = summaries[ticker];
                return (
                  <TableRow
                    key={ticker}
                    hover
                    onClick={() => handleRowClick(ticker)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Typography variant="body1" fontWeight="bold">
                        {ticker}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {summary ? formatCurrency(summary.latest_price) : '-'}
                    </TableCell>
                    <TableCell
                      align="right"
                      style={{
                        color: summary ? getPriceColor(summary.change_percent || 0) : 'inherit',
                        fontWeight: 'bold',
                      }}
                    >
                      {summary ? formatPercent(summary.change_percent || 0) : '-'}
                    </TableCell>
                    <TableCell align="right">
                      {summary && summary.rsi ? summary.rsi.toFixed(2) : '-'}
                    </TableCell>
                  </TableRow>
                );
              })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        component="div"
        count={filteredStocks.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[5, 10, 25, 50]}
      />
    </Paper>
  );
};

export default StockList;