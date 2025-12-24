-- ===================================================
-- SCRIPT KHỞI TẠO DATABASE SCHEMA
-- Tự động chạy khi TimescaleDB khởi động lần đầu tiên
-- ===================================================
-- Tạo TimescaleDB extention nếu chưa tồn tại
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE SCHEMA IF NOT EXISTS stock;

-- Tạo bảng information lưu trữ thông tin cơ bản và hồ sơ công ty
CREATE TABLE
    stock.information (
        exchange TEXT, -- Sàn giao dịch (ví dụ: HOSE, HNX, NASDAQ)
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        company_name TEXT, -- Tên công ty
        company_profile TEXT, -- Hồ sơ công ty
        industry TEXT, -- Ngành nghề kinh doanh
        no_shareholders INT, -- Số lượng cổ đông
        foreign_percent DOUBLE PRECISION, -- Tỷ lệ sở hữu của cổ đông nước ngoài (%)
        established_year INT, -- Năm thành lập
        no_employees INT, -- Số lượng nhân viên
        website TEXT, -- Trang web công ty
        history_dev TEXT, -- Lịch sử phát triển
        company_promise TEXT, -- Cam kết của công ty
        business_risk TEXT, -- Rủi ro kinh doanh
        key_developments TEXT, -- Các phát triển chính
        business_strategies TEXT, -- Chiến lược kinh doanh
        PRIMARY KEY (ticker) -- Khóa chính là mã chứng khoán
    );

-- Tạo bảng stock_prices_1m để lưu dữ liệu giá cổ phiếu theo khung thời gian 1 phút
CREATE TABLE
    stock.stock_prices_1m (
        time TIMESTAMPTZ NOT NULL, -- Thời gian ghi nhận dữ liệu
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        open DOUBLE PRECISION, -- Giá mở cửa
        high DOUBLE PRECISION, -- Giá cao nhất
        low DOUBLE PRECISION, -- Giá thấp nhất
        close DOUBLE PRECISION, -- Giá đóng cửa
        volume BIGINT, -- Khối lượng giao dịch
        PRIMARY KEY (time, ticker)
    );

-- Chuyển bảng thành hypertable để tối ưu lưu trữ và truy vấn thời gian
SELECT
    create_hypertable ('stock.stock_prices_1m', 'time');

-- Tạo composite index tối ưu cho query pattern phổ biến (filter theo ticker + time range)
CREATE INDEX idx_ticker_time ON stock.stock_prices_1m (ticker, time DESC);

-- Tạo index trên cột time để tăng tốc truy vấn theo thời gian
CREATE INDEX ON stock.stock_prices_1m (time DESC);

-- Tạo bảng stock_prices_1d để lưu trữ dữ liệu giá cổ phiếu theo khung thời gian 1 ngày
CREATE TABLE
    stock.stock_prices_1d (
        time DATE NOT NULL, -- Thời gian giao dịch
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        open DOUBLE PRECISION, -- Giá mở cửa
        high DOUBLE PRECISION, -- Giá cao nhất
        low DOUBLE PRECISION, -- Giá thấp nhất
        close DOUBLE PRECISION, -- Giá đóng cửa
        volume DOUBLE PRECISION, -- Khối lượng giao dịch
        avg_volume_5 DOUBLE PRECISION, -- Khối lượng giao dịch trung bình 5 phiên
        avg_volume_10 DOUBLE PRECISION, -- Khối lượng giao dịch trung bình 10 phiên
        avg_volume_20 DOUBLE PRECISION, -- Khối lượng giao dịch trung bình 20 phiên
        ma5 DOUBLE PRECISION, -- Đường trung bình động 5 ngày
        ma10 DOUBLE PRECISION, -- Đường trung bình động 10 ngày
        ma20 DOUBLE PRECISION, -- Đường trung bình động 20 ngày
        ma50 DOUBLE PRECISION, -- Đường trung bình động 50 ngày
        ma100 DOUBLE PRECISION, -- Đường trung bình động 100 ngày
        bb_upper DOUBLE PRECISION, -- Đường trên dải Bollinger
        bb_middle DOUBLE PRECISION, -- Đường giữa dải Bollinger
        bb_lower DOUBLE PRECISION, -- Đường dưới dải Bollinger
        rsi DOUBLE PRECISION, -- Chỉ số sức mạnh tương đối (RSI)
        macd_main DOUBLE PRECISION, -- Đường chính của MACD 
        macd_signal DOUBLE PRECISION, -- Đường tín hiệu của MACD
        macd_diff DOUBLE PRECISION, -- Đường chênh lệch của MACD (macd_main - macd_signal)
        PRIMARY KEY (time, ticker) -- Khóa chính là kết hợp thời gian và mã chứng khoán
    );

-- Chuyển bảng thành hypertable để tối ưu lưu trữ và truy vấn thời gian
SELECT
    create_hypertable ('stock.stock_prices_1d', 'time');

-- Tạo composite index tối ưu cho query pattern phổ biến (filter theo ticker + time range)
CREATE INDEX idx_ticker_time_1d ON stock.stock_prices_1d (ticker, time DESC);

-- Tạo index trên cột time để tăng tốc độ truy vấn theo thời gian
CREATE INDEX ON stock.stock_prices_1d (time DESC);

-- Tạo bảng balance_sheet để lưu trữ bảng cân đối kế toán
CREATE TABLE
    stock.balance_sheet (
        ticker varchar(20) NOT NULL, -- Mã chứng khoán
        year int4 NOT NULL, -- Năm tài chính
        quarter int4 NOT NULL CHECK (quarter >= 1 AND quarter <= 4), -- Quý tài chính
        accounts_receivable numeric NULL, -- Các khoản phải thu
        advances_from_customers numeric NULL, -- Tiền ứng trước từ khách hàng
        available_for_sale_securities numeric NULL, -- Chứng khoán sẵn sàng để bán
        balances_with_sbv numeric NULL, -- Số dư với SBV 
        budget_sources_and_other_funds numeric NULL, -- Nguồn vốn ngân sách và các quỹ khác
        current_liabilities numeric NULL, -- Nợ ngắn hạn
        current_assets numeric NULL, -- Tài sản ngắn hạn
        capital numeric NULL, -- Vốn chủ sở hữu
        capital_and_reserves numeric NULL, -- Vốn và quỹ dự trữ 
        cash_and_cash_equivalents numeric NULL, -- Tiền và các khoản tương đương Tiền
        common_shares numeric NULL, -- Cổ phiếu phổ thông
        convertible_bonds numeric NULL, -- Trái phiếu chuyển đổi
        convertible_bonds_cds_other_valuable_papers_issued numeric NULL, -- Trái phiếu chuyển đổi, CDS và các giấy tờ có giá khác phát hành
        deposits_and_borrowings_from_other_credit_institutions numeric NULL, -- Tiền gửi và vay từ các tổ chức tín dụng khác 
        deposits_from_customers numeric NULL, -- Tiền gửi từ khách hàng
        derivatives_and_other_financial_liabilities numeric NULL, -- Các công cụ phái sinh và các khoản nợ tài chính khác 
        diffences_upon_assets_revaluation numeric NULL, -- Chênh lệch đánh giá lại tài sản
        due_to_gov_and_borrowings_from_sbv numeric NULL, -- Nợ phải trả chính phủ và vay từ SBV
        fixed_assets numeric NULL, -- Tài sản cố định
        foreign_curency_difference_reserve numeric NULL, -- Dự phòng chênh lệch tỉ giá ngoại tệ
        funds_received_from_gov_international_other_institutions numeric NULL, -- Quỹ nhận từ chính phủ, tổ chức quốc tế và các tổ chức khác
        goodwill numeric NULL, -- Lợi thế thương mại
        held_to_maturity_securities numeric NULL, -- Chứng khoán nắm giữ đến ngày đáo hạn
        intangible_fixed_assets numeric NULL, -- Tài sản cố định vô hình
        investment_securities numeric NULL, -- Chứng khoán đầu tư 
        investment_and_development_funds numeric NULL, -- Quỹ đầu tư và phát triển
        investment_in_joint_ventures numeric NULL, -- Đầu tư vào liên doanh
        investment_in_properties numeric NULL, -- Đầu tư vào bất động sản
        investment_in_associates_companies numeric NULL, -- Đầu tư vào công ty liên kết
        liabilities numeric NULL, -- Tổng nợ phải trả
        long_term_assets numeric NULL, -- Tài sản dài hạn
        leased_assets numeric NULL, -- Tài sản thuê tài chính
        provision_for_diminution_in_value_of_long_term_investments numeric NULL, -- Dự phòng giảm giá trị đầu tư dài hạn
        provision_for_diminution_in_value_of_investment_securities numeric NULL, -- Dự phòng giảm giá trị chứng khoán đầu tư
        provision_for_losses_on_loans_and_advances_to_customers numeric NULL, -- Dự phòng tổn thất cho các khoản cho vay và ứng trước cho khách hàng 
        loans_and_advances_to_customers numeric NULL, -- Các khoản cho vay và ứng trước cho khách hàng 
        loans_and_advances_to_customers_net numeric NULL, -- Các khoản cho vay và ứng trước cho khách hàng (sau dự phòng)
        long_term_borrowings numeric NULL, -- Khoản vay dài hạn
        long_term_investments numeric NULL, -- Đầu tư dài hạn
        long_term_liabilities numeric NULL, -- Tất cả các khoản nợ và nghĩa vụ phải trả dài hạn
        long_term_loans_receivables numeric NULL, -- Các khoản cho vay dài hạn
        long_term_prepayments numeric NULL, -- Chi phí trả trước dài hạn
        long_term_trade_receivables numeric NULL, -- Các khoản phải thu dài hạn
        minority_interests numeric NULL, -- Lợi ích thiểu số
        net_inventories numeric NULL, -- Giá trị hàng tồn kho ròng
        owners_equity numeric NULL, -- Vốn chủ sở hữu của cổ đông
        other_assets numeric NULL, -- Tài sản khác 
        other_reserves numeric NULL, -- Quỹ dự trữ khác 
        other_current_assets numeric NULL, -- Tài sản ngắn hạn
        other_current_assets_bn numeric NULL, -- Tài sản ngắn hạn khác (BN)
        other_liabilities numeric NULL, -- Nợ phải trả khác 
        other_long_term_assets numeric NULL, -- Tài sản dài hạn khác 
        other_long_term_receivables numeric NULL, -- Các khoản phải thu dài hạn khác 
        other_non_current_assets numeric NULL, -- Tài sản phi lưu động khác 
        paid_in_capital numeric NULL, -- Vốn góp
        placements_with_and_loans_to_other_credit_institutions numeric NULL, -- Tiền gửi và cho vay vào các tổ chức tín dụng 
        prepayments_to_suppliers numeric NULL, -- Chi phí trả trước cho nhà cung cấp
        provision_for_diminution_in_value_of_trading_securities numeric NULL, -- Dự phòng giảm giá trị chứng khoán kinh doanh 
        reserves numeric NULL, -- Quỹ dự trữ 
        short_term_borrowings numeric NULL, -- Vay ngắn hạn 
        short_term_investments numeric NULL, -- Đầu tư ngắn hạn
        short_term_loans_receivables numeric NULL, -- Các khoản cho vay ngắn hạn
        total_assets numeric NULL, -- Tổng tài sản
        total_resources numeric NULL, -- Tổng nguồn vốn
        tangible_fixed_assets numeric NULL, -- Tài sản cố định hữu hình
        trading_securities numeric NULL, -- Chứng khoán kinh doanh 
        trading_securities_net numeric NULL, -- Chứng khoán kinh doanh sau dự phòng
        undistributed_earnings numeric NULL, -- Lợi nhuận chưa phân phối
        CONSTRAINT pk_balance_sheet PRIMARY KEY (ticker, year, quarter),
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index cho bảng balance_sheet
CREATE INDEX idx_balance_sheet_ticker ON stock.balance_sheet(ticker);
CREATE INDEX idx_balance_sheet_ticker_year_quarter ON stock.balance_sheet(year DESC, quarter DESC);

-- Tạo bảng cash_flow để lưu trữ dữ liệu báo cáo lưu chuyển tiền tệ 
CREATE TABLE
    stock.cash_flow (
        ticker varchar(20) NOT NULL, -- Mã chứng khoán 
        year int4 NOT NULL, -- Năm tài chính
        quarter int4 NOT NULL CHECK (quarter >= 1 AND quarter <= 4), -- Quý tài chính
        business_income_tax_paid numeric NULL, -- Tiền thuế thu nhập doanh nghiệp đã nộp
        cash_and_cash_equivalents_at_end_of_period numeric NULL, -- Tiền và các khoản tương đương tiền cuối kỳ 
        cash_and_cash_equivalents numeric NULL, -- Tiền và các khoản tương đương tiền 
        cash_flows_from_financial_activities numeric NULL, -- Lưu chuyển tiền từ hoạt động tài chính
        collections_of_loans_proceeds_from_sales_dept_instruments_bnv numeric NULL, -- Thu hồi các quản cho vay, tiền thu từ bán các công nợ (BNV) 
        depreciation_and_amortization numeric NULL, -- Khấu hao tài sản cố định và tài sản vô hình
        dividends_paid numeric NULL, -- Tiền cổ tức đã trả 
        finance_lease_principal_payments numeric NULL, -- Thanh toán gốc thuê tài chính
        foreign_exchange_difference_adjustments numeric NULL, -- Điều chỉnh chênh lệch tỉ giá ngoại tệ 
        gain_on_dividend numeric NULL, -- Lợi nhuận từ cổ tức 
        increase_in_chapter_capital numeric NULL, -- Tăng vốn điều lệ 
        increase_decrease_in_inventories numeric NULL, -- Tăng/giảm hàng tồn kho 
        increase_decrease_in_payables numeric NULL, -- Tăng/Giảm các khoản phải trả 
        increase_decrease_in_prepaid_expenses numeric NULL, -- Tăng/Giảm chi phí trả trước
        increase_decrease_in_receivables numeric NULL, -- Tăng/Giảm các khoản phải thu
        interest_expense numeric NULL, -- Chi phí lãi vay 
        interest_income_and_dividends numeric NULL, -- Thu nhập lãi và cổ tức 
        interest_paid numeric NULL, -- Tiền lãi đã trả 
        investment_in_other_entities numeric NULL, -- Đầu tư vào các thực thể khác 
        loans_granted_purchases_of_debt_instrucments_bnvnd numeric NULL, -- Các khoản cho vay được cấp, mua các công cụ nợ (BNV)
        net_cash_flows_from_investing_activities numeric NULL, -- Lưu chuyển tiền tệ thuần từ hoạt động đầu tư 
        net_cash_flows_from_operating_activities_before_bit numeric NULL, -- Lưu chuyển tiền thuần từ hoạt động kinh doanh trước thuế TNDN 
        net_profit_loss_before_tax numeric NULL, -- Lợi nhuận (lỗ) trước thuế 
        net_cash_infows_outflows_from_operating_activities numeric NULL, -- Lưu chuyển tiền thuần từ hoạt động kinh doanh
        net_increase_decrease_in_cash_and_cash_equivalents numeric NULL, -- Tăng giảm dòng tiền và các hoạt động tương đường tiền 
        operating_profit_before_changes_in_working_capital numeric NULL, -- Lợi nhuận từ hoạt động kinh doanh trước thay đổi vốn lưu động 
        other_payments_on_operating_activities numeric NULL, -- Các khoản chi phí khác cho hoạt động kinh doanh 
        other_receipts_from_operating_activities numeric NULL, -- Các khoản thu khác từ hoạt động kinh doanh 
        payment_from_reserves numeric NULL, -- Tiền chi từ quỹ dự phòng 
        payment_for_shares_repurchased numeric NULL, -- Tiền chi mua lại cổ phiếu 
        proceeds_from_borrowings numeric NULL, -- Tiền thu từ đi vay 
        proceeds_from_disposal_of_fixed_assets numeric NULL, -- Tiền thu từ thanh lý tài sản cố định
        proceeds_from_divestments_in_other_entities numeric NULL, -- Tiền thu từ việc thoái vốn đầu tư vào các thực thể khác 
        profit_loss_from_disposal_of_fixed_assets numeric NULL, -- Lãi/lỗ từ thanh lý tài sản cố định
        profit_loss_from_investing_activities numeric NULL, -- Lãi/lỗ từ hoạt động đầu tư 
        profits_from_other_activities numeric NULL, -- Lợi nhuận từ các hoạt động khác 
        provision_for_credit_losses numeric NULL, -- Dự phòng tổn thất tín dụng
        purchase_of_fixed_assets numeric NULL, -- Tiền chi mua tài sản cố định
        repayment_of_borrowings numeric NULL, -- Tiền chi trả nợ vay
        unrealized_foreign_exchange_gain_loss numeric NULL, -- Lãi/ lỗ chênh lệch tỉ giá chưa thực hiện
        CONSTRAINT pk_cash_flow PRIMARY KEY (ticker, year, quarter),
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE 
    );

-- Tạo index cho bảng cash_flow
CREATE INDEX idx_cash_flow_ticker ON stock.cash_flow(ticker);
CREATE INDEX idx_cash_flow_year_quarter ON stock.cash_flow(year DESC, quarter DESC);

-- Tạo bảng income_statement để lưu trữ dữ liệu báo cáo kết quả hoạt động kinh doanh 
CREATE TABLE
    stock.income_statement (
        ticker varchar(20) NOT NULL, -- Mã chứng khoán
        year int4 NOT NULL, -- Năm tài chính
        quarter int4 NOT NULL CHECK (quarter >= 1 AND quarter <= 4), -- Quý tài chính
        attributable_to_parent_company numeric NULL, -- Lợi nhuận thuộc về công ty mẹ
        attribute_to_parent_company_bnvnd numeric NULL, -- Lợi nhuận thuộc về công ty mẹ (BNVND)
        attribute_to_parent_company_yoy numeric NULL, -- Lợi nhuận thuộc về công ty mẹ (YOY) 
        business_income_tax_current numeric NULL, -- Thuế thu nhập doanh nghiệp hiện hành
        business_income_tax_deferred numeric NULL, -- Thuế thu nhập doanh nghiệp hoãn lại 
        cost_of_sales numeric NULL, -- Giá vốn hàng bán 
        dividends_received numeric NULL, -- Cổ tức nhận được 
        eps_basic numeric NULL, -- Lợi nhuận cơ bản trên cổ phiếu (EPS basic)
        fees_and_commissions_expenses numeric NULL, -- Chi phí phí và hoa hồng
        fees_and_commission_income numeric NULL, -- Thu nhập phí và hoa hồng
        financial_expenses numeric NULL, -- Chi phí tài chính
        financial_income numeric NULL, -- Thu nhập tài chính
        gain_loss_from_joint_ventures numeric NULL, -- Lãi/lỗ từ các liên doanh 
        general_admin_expenses numeric NULL, -- Chi phí quản lý chung
        gross_profit numeric NULL, -- Lợi nhuận gộp
        interest_expenses numeric NULL, -- Chi phí lãi vay
        interest_and_similar_expenses numeric NULL, -- Chi phí lãi vay và chi phí tương tự 
        interest_and_similar_income numeric NULL, -- Thu nhập lãi vay và thu nhập tương tự 
        minority_interests numeric NULL, -- Lợi ích thiểu số 
        net_fee_and_commision_income numeric NULL, -- Lợi nhuận thuần từ phí và hoạt động kinh doanh 
        net_interest_income numeric NULL, -- Lợi nhuận thuần từ lãi vay 
        net_other_income_expenses numeric NULL, -- Lợi nhuận thuần từ hoạt động khách
        net_profit_for_the_year numeric NULL, -- Lợi nhuận thuần trong năm 
        net_sales numeric NULL, -- Doanh thu thuần
        net_gain_loss_from_disposal_of_investment_securities numeric NULL, -- Lãi lỗ thuần từ thanh lý chứng khoán đầu tư
        net_gain_loss_from_foreign_currency_and_gold_dealings numeric NULL, -- Lãi lỗ thuần từ kinh doanh ngoại tệ và vàng 
        net_gain_loss_from_trading_of_trading_securities numeric NULL, -- Lãi lỗ thuần từ kinh doanh chứng khoán
        net_income_from_associated_companies numeric NULL, -- Thu nhập ròng từ các công ty liên kết
        operating_profit_before_provision numeric NULL, -- Lợi nhuận hoạt động trước dự phòng 
        operating_profit_loss numeric NULL, -- Lợi nhuận (lỗ) từ hoạt động kinh doanh 
        other_income_expenses numeric NULL, -- Thu nhập (chi phí) khác 
        other_expenses numeric NULL, -- Chi phí khác 
        other_income numeric NULL, -- Thu nhập khác 
        profit_before_tax numeric NULL, -- Lợi nhuận trước thuế 
        provision_for_credit_losses numeric NULL, -- Dự phòng tổn thất tín dụng
        revenue_bnvnd numeric NULL, -- Doanh thu (tỷ VNĐ)
        revenue_yoy numeric NULL, -- Tăng trưởng doanh thu theo năm (YoY) 
        sales numeric NULL, -- Doanh thu bán hàng 
        sales_dedutions numeric NULL, -- Các khoản giảm trừ doanh thu 
        selling_expenses numeric NULL, -- Chi phí bán hàng 
        tax_for_the_year numeric NULL, -- Thuế trong năm 
        total_operating_revennue numeric NULL, -- Tổng doanh thu hoạt động 
        CONSTRAINT pk_income_statement PRIMARY KEY (ticker, year, quarter),
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index cho bảng income_statement
CREATE INDEX idx_income_statement_ticker ON stock.income_statement(ticker);
CREATE INDEX idx_income_statement_year_quarter ON stock.income_statement(year DESC, quarter DESC);

-- Tạo bảng ratio lưu trữ các chỉ số tài chính
CREATE TABLE
    stock.ratio (
        ticker varchar(20) NOT NULL, -- Mã chứng khoán
        year int4 NOT NULL, -- Năm tài chính
        quarter int4 NOT NULL CHECK (quarter >= 1 AND quarter <= 4), -- Quý tài chính 
        -- Chỉ số đòn bẩy tài chính (Leverage Ratio)
        stltborrowings_equity numeric NULL, -- Tỷ lệ nợ ngắn hạn + nợ dài hạn trên vốn chủ sở hữu
        debt_equity numeric NULL, -- Tỷ lệ nợ trên vốn chủ sở hữu (Debt to Equity)
        fixedasset_equity numeric NULL, -- Tỷ lệ tài sản cố định trên vốn chủ sở hữu 
        ownersequity_chartercapital numeric NULL, -- Tỷ lệ vốn chủ sở hữu trên vốn điều lệ 
        financial_leverage numeric NULL, -- Đòn bẩy tài chính
        -- Chỉ số hiệu quả hoạt động (Efficiency/Turnover Ratios)
        asset_turnover numeric NULL, -- Vòng quay tài sản 
        cash_cycle numeric NULL, -- Chu kì tiền mặt 
        days_inventory_outstanding numeric NULL, -- Số ngày tồn kho 
        days_payable_outstanding numeric NULL, -- Số ngày phải trả
        day_sales_outstanding numeric NULL, -- Số ngày thu tiền 
        fixedasset_turnover numeric NULL, -- Vòng quay tài sản cố định
        inventory_turnover numeric NULL, -- Vòng quay hàng tồn kho 
        -- Chỉ số khả năng sinh lời (Profitability Ratios)
        dividend_yfield numeric NULL, -- Tỷ suất cổ tức 
        ebit numeric NULL, -- Lợi nhuận trước lãi vay và thuế 
        ebit_margin numeric NULL, -- Tỷ suất lợi nhuận EBIT 
        ebitda numeric NULL, -- Lợi nhuận trước lãi vay, thuế và khấu hao 
        gross_profit_margin numeric NULL, -- Tỷ suất lợi nhuận gộp
        net_profit_margin numeric NULL, -- Tỷ suất lợi nhuận ròng 
        roa numeric NULL, -- Tỷ suất sinh lời trên tài sản (Return on Assets)
        roe numeric NULL, -- Tỷ suất sinh lời trên vốn chủ sở hữu (Return on Equity)
        roic numeric NULL, -- Tỷ suất sinh lời trên vốn đầu tư (Return on Invested Capital)
        -- Chỉ số thanh khoản (Liquidity Ratios)
        cash_ratio numeric NULL, -- Tỷ số tiền mặt
        current_ratio numeric NULL, -- Tỷ số thanh toán hiện hành
        interest_coverage numeric NULL, -- Khả năng thanh toán lãi vay 
        quick_ratio numeric NULL, -- Tỷ số thanh toán nhanh 
        -- Chỉ số định giá (Valuation Ratios)
        bvps numeric NULL, -- Giá trị sổ sách trên mỗi cổ phiếu (Book Value Per Share)
        eps numeric NULL, -- Thu nhập trên mỗi cổ phiếu (Earnings Per Share) 
        ev_ebitda numeric NULL, -- Tỷ lệ giá trị doanh nghiệp trên EBITDA (Enterprise Value to EBITDA) 
        market_capital numeric NULL, -- Vốn hóa thị trường
        outstanding_share numeric NULL, -- Số lượng cổ phiếu đang lưu hành
        pb numeric NULL, -- Tỉ lệ giá trên giá trị sổ sách (Price to book)
        p_cashflow numeric NULL, -- Tỷ lệ giá trên dòng tiền (Price to Cash Flow)
        pe numeric NULL, -- Tỷ lệ giá trên thu nhập (Price to Earnings)
        ps numeric NULL, -- Tỷ lệ giá trên doanh thu (Price to Sales)
        CONSTRAINT pk_ratio PRIMARY KEY (ticker, year, quarter),
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index cho bảng ratio
CREATE INDEX idx_ratio_ticker ON stock.ratio(ticker);
CREATE INDEX idx_ratio_year_quarter ON stock.ratio(year DESC, quarter DESC);

-- Tạo bảng stock_prices_3d_predict để lưu trữ dự đoán giá cổ phiếu 3 ngày 
CREATE TABLE
    stock.stock_prices_3d_predict (
        time DATE NOT NULL, -- Thời gian dự đoán
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        close_next_1 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 1
        close_next_2 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 2
        close_next_3 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 3
        CONSTRAINT pk_stock_prices_3d_predict PRIMARY KEY (time, ticker) -- Khóa chính là kết hợp thời gian và mã chứng khoán
    );

-- Chuyển bảng thành hypertable để tối ưu lưu trữ và truy vấn thời gian
SELECT
    create_hypertable ('stock.stock_prices_3d_predict', 'time');

-- Tạo index trên cột ticker để tăng tốc truy vấn theo mã chứng khoán
CREATE INDEX stock_prices_3d_predict_ticker_idx ON stock.stock_prices_3d_predict USING btree (ticker);

-- Tạo index trên cột time để tăng tốc truy vấn theo thời gian
CREATE INDEX stock_prices_3d_predict_time_idx ON stock.stock_prices_3d_predict USING btree (time DESC);

-- Tạo bảng stock_prices_48d_predict để lưu trữ dự đoán giá cổ phiếu 48 ngày 
CREATE TABLE
    stock.stock_prices_48d_predict (
        time DATE NOT NULL, -- Thời gian dự đoán
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        close_next_1 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 1
        close_next_2 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 2
        close_next_3 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 3
        close_next_4 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 4
        close_next_5 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 5
        close_next_6 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 6
        close_next_7 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 7
        close_next_8 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 8
        close_next_9 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 9
        close_next_10 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 10
        close_next_11 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 11
        close_next_12 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 12
        close_next_13 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 13
        close_next_14 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 14
        close_next_15 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 15
        close_next_16 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 16
        close_next_17 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 17
        close_next_18 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 18
        close_next_19 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 19
        close_next_20 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 20
        close_next_21 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 21
        close_next_22 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 22
        close_next_23 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 23
        close_next_24 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 24
        close_next_25 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 25
        close_next_26 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 26
        close_next_27 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 27
        close_next_28 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 28
        close_next_29 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 29
        close_next_30 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 30
        close_next_31 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 31
        close_next_32 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 32
        close_next_33 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 33
        close_next_34 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 34
        close_next_35 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 35
        close_next_36 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 36
        close_next_37 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 37
        close_next_38 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 38
        close_next_39 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 39
        close_next_40 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 40
        close_next_41 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 41
        close_next_42 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 42
        close_next_43 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 43
        close_next_44 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 44
        close_next_45 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 45
        close_next_46 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 46
        close_next_47 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 47
        close_next_48 FLOAT8 NULL, -- Giá đóng cửa dự đoán ngày 48
        CONSTRAINT pk_stock_prices_48d_predict PRIMARY KEY (time, ticker) -- Khóa chính là kết hợp thời gian và mã chứng khoán
    );

-- Chuyển thành bảng hypertable để tối ưu lưu trữ và truy vấn thời gian
SELECT
    create_hypertable ('stock.stock_prices_48d_predict', 'time');

-- Tạo index trên cột ticker để tăng tốc truy vấn theo mã chứng khoán
CREATE INDEX stock_prices_48d_predict_ticker_idx ON stock.stock_prices_48d_predict USING btree (ticker);

-- Tạo index trên cột time để tăng tốc truy vấn theo thời gian 
CREATE INDEX stock_prices_48d_predict_time_idx ON stock.stock_prices_48d_predict USING btree (time DESC);

-- Tạo bảng Alert để lưu trữ dữ liệu cảnh báo người dùng
CREATE TABLE
    stock.alert (
        id SERIAL4 NOT NULL, -- ID tăng tự động
        user_id INT8 NOT NULL, -- ID người dùng
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        type VARCHAR(20) NOT NULL, -- Loại cảnh báo (price, avg_volume_5, avg_volume_10, avg_volume_20, ma5, ma10, ma20, ma50, ma100, bb_upper, bb_middle, bb_lower, rsi, macd_diff, macd_main, macd_signal)
        condition VARCHAR(20) NOT NULL, -- Điều kiện cảnh báo (above, below, cross_above, cross_below, above_70, neg_to_pos, pos_to_neg)
        price_value NUMERIC(18,2) NULL, -- Giá trị ngưỡng cảnh báo 
        create_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Thời gian tạo cảnh báo 
        user_name VARCHAR(255) NULL, -- Tên người dùng
        CONSTRAINT alert_pkey PRIMARY KEY (id), -- Khóa chính
        CONSTRAINT check_alert_type CHECK (((type)::text = ANY ((ARRAY['price'::character varying, 'avg_volume_5'::character varying, 'avg_volume_10'::character varying, 'avg_volume_20':: character varying, 'ma5'::character varying, 'ma10'::character varying, 'ma20'::character varying, 'ma50'::character varying, 'ma100'::character varying, 'bb_upper'::character varying, 'bb_middle'::character varying, 'bb_lower'::character varying, 'rsi'::character varying, 'macd_diff'::character varying, 'macd_main'::character varying, 'macd_signal'::character varying])::text[]))), -- Kiểm tra loại cảnh báo hợp lệ 
        CONSTRAINT check_condition CHECK (((condition)::text = ANY ((ARRAY['above'::character varying, 'below'::character varying, 'cross_above'::character varying, 'cross_below'::character varying, 'above_70'::character varying, 'neg_to_pos'::character varying, 'pos_to_neg'::character varying])::text[]))), -- Kiểm tra điều kiện cảnh báo hợp lệ   
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index trên cột ticker để tăng tốc truy vấn theo mã chứng khoán
CREATE INDEX idx_alert_ticker ON stock.alert USING btree(ticker);

-- Tạo index trên cột user_id để tăng tốc truy vấn theo người dùng
CREATE INDEX idx_alert_user_id ON stock.alert USING btree(user_id);

-- Tạo bảng technical_alerts để lưu trữ cảnh báo kỹ thuật tự động
CREATE TABLE
    stock.technical_alerts (
        id SERIAL PRIMARY KEY, -- ID tự động tăng
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        alert_type VARCHAR(50) NOT NULL, -- Loại cảnh báo: rsi_overbought, rsi_oversold, golden_cross, death_cross, volume_spike, macd_bullish, macd_bearish
        alert_level VARCHAR(20) NOT NULL, -- Mức độ: critical, warning, info
        message TEXT NOT NULL, -- Nội dung cảnh báo
        indicator_value DOUBLE PRECISION, -- Giá trị chỉ báo tại thời điểm phát hiện
        price_at_alert DOUBLE PRECISION, -- Giá cổ phiếu tại thời điểm phát hiện
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Thời gian tạo cảnh báo
        is_active BOOLEAN DEFAULT TRUE, -- Cảnh báo còn hiệu lực hay không
        CONSTRAINT check_technical_alert_type CHECK (
            alert_type IN (
                'rsi_overbought', 'rsi_oversold',
                'golden_cross', 'death_cross',
                'volume_spike', 'volume_low',
                'macd_bullish', 'macd_bearish',
                'bb_squeeze', 'bb_breakout'
            )
        ),
        CONSTRAINT check_technical_alert_level CHECK (
            alert_level IN ('critical', 'warning', 'info')
        ),
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index để tăng tốc truy vấn technical_alerts
CREATE INDEX idx_technical_alerts_ticker ON stock.technical_alerts(ticker);
CREATE INDEX idx_technical_alerts_created_at ON stock.technical_alerts(created_at DESC);
CREATE INDEX idx_technical_alerts_type ON stock.technical_alerts(alert_type);
CREATE INDEX idx_technical_alerts_level ON stock.technical_alerts(alert_level);
CREATE INDEX idx_technical_alerts_active ON stock.technical_alerts(is_active);
CREATE INDEX idx_technical_alerts_ticker_active_created ON stock.technical_alerts(ticker, is_active, created_at DESC);

-- Comment mô tả bảng technical_alerts
COMMENT ON TABLE stock.technical_alerts IS 'Cảnh báo kỹ thuật tự động được hệ thống phát hiện dựa trên các chỉ báo kỹ thuật';
COMMENT ON COLUMN stock.technical_alerts.alert_type IS 'Loại cảnh báo: rsi_overbought, rsi_oversold, golden_cross, death_cross, volume_spike, macd_bullish, macd_bearish';
COMMENT ON COLUMN stock.technical_alerts.alert_level IS 'Mức độ: critical (nghiêm trọng), warning (cảnh báo), info (thông tin)';
COMMENT ON COLUMN stock.technical_alerts.is_active IS 'Cảnh báo còn hiệu lực (true) hay đã hết hiệu lực (false)';

-- Tạo bảng subscribe để lưu trữ danh sách theo dõi cổ phiếu của người dùng 
CREATE TABLE 
    stock.subscribe(
        id SERIAL4 NOT NULL, -- ID tự động tăng 
        user_id INT8 NOT NULL, -- ID người dùng 
        ticker VARCHAR(20) NOT NULL, -- Mã chứng khoán
        create_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL, -- Thời gian tạo theo dõi 
        user_name VARCHAR(255) NOT NULL, -- Tên người dùng 
        CONSTRAINT subscribe_pkey PRIMARY KEY (id), -- Khóa chính
        CONSTRAINT subscribe_user_id_ticker_key UNIQUE (user_id, ticker), -- Đảm bảo mỗi người dùng chỉ theo dõi một mã chứng khoán một lần 
        FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
    );

-- Tạo index trên cột ticker để tăng tốc độ truy vấn theo mã chứng khoán
CREATE INDEX idx_subscribe_ticker ON stock.subscribe USING btree(ticker);

-- Tạo index trên cột user_id để tăng tốc độ truy vấn theo người dùng 
CREATE INDEX idx_subscribe_user_id ON stock.subscribe USING btree(user_id);
