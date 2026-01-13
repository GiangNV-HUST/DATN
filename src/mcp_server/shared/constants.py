"""
Shared constants for MCP server
Contains validation constants for stocks, alert types, and conditions
"""

# VN30 Stock List - 30 blue-chip stocks in Vietnam
VN30_STOCKS = {
    'ACB': 'Ngân hàng TMCP Á Châu',
    'BCM': 'Tổng Công ty Đầu tư và Phát triển Công nghiệp',
    'BID': 'Ngân hàng TMCP Đầu tư và Phát triển Việt Nam',
    'BVH': 'Tập đoàn Bảo Việt',
    'CTG': 'Ngân hàng TMCP Công thương Việt Nam',
    'FPT': 'Công ty Cổ phần FPT',
    'GAS': 'Tổng Công ty Khí Việt Nam',
    'GVR': 'Tập đoàn Công nghiệp Cao su Việt Nam',
    'HDB': 'Ngân hàng TMCP Phát Triển TP.HCM',
    'HPG': 'Công ty CP Tập đoàn Hòa Phát',
    'MBB': 'Ngân hàng TMCP Quân đội',
    'MSN': 'Công ty CP Tập đoàn Masan',
    'MWG': 'Công ty CP Đầu tư Thế Giới Di Động',
    'PLX': 'Tập đoàn Xăng dầu Việt Nam',
    'LPB': 'Ngân hàng TMCP Lộc Phát Việt Nam',
    'SAB': 'TỔNG CTCP Bia - Rượu - NGK Sài Gòn',
    'SHB': 'Ngân hàng TMCP Sài Gòn – Hà Nội',
    'SSB': 'Ngân hàng TMCP Đông Nam Á',
    'SSI': 'Công ty CP Chứng khoán SSI',
    'STB': 'Ngân hàng TMCP Sài Gòn Thương Tín',
    'TCB': 'Ngân hàng TMCP Kỹ thương Việt Nam',
    'TPB': 'Ngân hàng TMCP Tiên Phong',
    'VCB': 'Ngân hàng TMCP Ngoại thương Việt Nam',
    'VHM': 'Công ty CP Vinhomes',
    'VIB': 'Ngân hàng TMCP Quốc tế Việt Nam',
    'VIC': 'Tập đoàn Vingroup',
    'VJC': 'Công ty CP Hàng không Vietjet',
    'VNM': 'Công ty CP Sữa Việt Nam',
    'VPB': 'Ngân hàng TMCP Việt Nam Thịnh Vượng',
    'VRE': 'Công ty CP Vincom Retail'
}

# Alert types with Vietnamese descriptions
ALERT_TYPES = {
    'price': 'Cảnh báo giá',
    'ma5': 'MA5',
    'ma10': 'MA10',
    'ma20': 'MA20',
    'ma50': 'MA50',
    'ma100': 'MA100',
    'bb_upper': 'Dải trên Bollinger',
    'bb_lower': 'Dải dưới Bollinger',
    'rsi': 'RSI',
    'macd': 'MACD',
    'volume_ma5': 'Khối lượng > TB 5 phiên',
    'volume_ma10': 'Khối lượng > TB 10 phiên',
    'volume_ma20': 'Khối lượng > TB 20 phiên'
}

# Valid conditions for each alert type
VALID_ALERT_CONDITIONS = {
    'price': ['above', 'below'],
    'ma5': ['cross_above', 'cross_below'],
    'ma10': ['cross_above', 'cross_below'],
    'ma20': ['cross_above', 'cross_below'],
    'ma50': ['cross_above', 'cross_below'],
    'ma100': ['cross_above', 'cross_below'],
    'bb_upper': ['cross_above', 'cross_below'],
    'bb_lower': ['cross_above', 'cross_below'],
    'rsi': ['above_70', 'below_30'],
    'macd': ['neg_to_pos', 'pos_to_neg', 'cross_above', 'cross_below'],
    'volume_ma5': ['above'],
    'volume_ma10': ['above'],
    'volume_ma20': ['above']
}

# Condition descriptions for better error messages
CONDITION_DESCRIPTIONS = {
    'price': {
        'above': 'giá trên mức',
        'below': 'giá dưới mức'
    },
    'ma5': {
        'cross_above': 'giá cắt lên trên MA5',
        'cross_below': 'giá cắt xuống dưới MA5'
    },
    'ma10': {
        'cross_above': 'giá cắt lên trên MA10',
        'cross_below': 'giá cắt xuống dưới MA10'
    },
    'ma20': {
        'cross_above': 'giá cắt lên trên MA20',
        'cross_below': 'giá cắt xuống dưới MA20'
    },
    'ma50': {
        'cross_above': 'giá cắt lên trên MA50',
        'cross_below': 'giá cắt xuống dưới MA50'
    },
    'ma100': {
        'cross_above': 'giá cắt lên trên MA100',
        'cross_below': 'giá cắt xuống dưới MA100'
    },
    'bb_upper': {
        'cross_above': 'giá cắt lên trên dải Bollinger trên',
        'cross_below': 'giá cắt xuống dưới dải Bollinger trên'
    },
    'bb_lower': {
        'cross_above': 'giá cắt lên trên dải Bollinger dưới',
        'cross_below': 'giá cắt xuống dưới dải Bollinger dưới'
    },
    'rsi': {
        'above_70': 'RSI trên 70 (quá mua)',
        'below_30': 'RSI dưới 30 (quá bán)'
    },
    'macd': {
        'neg_to_pos': 'MACD histogram từ âm sang dương',
        'pos_to_neg': 'MACD histogram từ dương sang âm',
        'cross_above': 'MACD cắt lên trên signal',
        'cross_below': 'MACD cắt xuống dưới signal'
    },
    'volume_ma5': {
        'above': 'khối lượng trên TB 5 phiên'
    },
    'volume_ma10': {
        'above': 'khối lượng trên TB 10 phiên'
    },
    'volume_ma20': {
        'above': 'khối lượng trên TB 20 phiên'
    }
}


def validate_symbol(symbol: str) -> tuple[bool, str]:
    """
    Validate if symbol is in VN30

    Args:
        symbol: Stock symbol to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    symbol = symbol.upper()
    if symbol not in VN30_STOCKS:
        return False, f"Mã cổ phiếu '{symbol}' không hợp lệ. Chỉ hỗ trợ VN30 stocks."
    return True, ""


def validate_alert_type(alert_type: str) -> tuple[bool, str]:
    """
    Validate if alert type is valid

    Args:
        alert_type: Alert type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if alert_type not in ALERT_TYPES:
        valid_types = ', '.join(ALERT_TYPES.keys())
        return False, f"Loại cảnh báo '{alert_type}' không hợp lệ. Các loại hợp lệ: {valid_types}"
    return True, ""


def validate_alert_condition(alert_type: str, condition: str) -> tuple[bool, str]:
    """
    Validate if condition is valid for the given alert type

    Args:
        alert_type: Alert type
        condition: Condition to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_conditions = VALID_ALERT_CONDITIONS.get(alert_type, [])
    if condition not in valid_conditions:
        valid_cond_str = ', '.join(valid_conditions)
        return False, f"Điều kiện '{condition}' không hợp lệ cho loại cảnh báo '{alert_type}'. Các điều kiện hợp lệ: {valid_cond_str}"
    return True, ""


def get_alert_description(alert_type: str, condition: str, value: float = None) -> str:
    """
    Get human-readable description of alert

    Args:
        alert_type: Alert type
        condition: Condition
        value: Optional value for price alerts

    Returns:
        Human-readable description
    """
    type_desc = ALERT_TYPES.get(alert_type, alert_type)
    cond_desc = CONDITION_DESCRIPTIONS.get(alert_type, {}).get(condition, condition)

    if alert_type == 'price' and value is not None:
        return f"{type_desc}: {cond_desc} {value:,.0f} VNĐ"
    else:
        return f"{type_desc}: {cond_desc}"


# Export all
__all__ = [
    'VN30_STOCKS',
    'ALERT_TYPES',
    'VALID_ALERT_CONDITIONS',
    'CONDITION_DESCRIPTIONS',
    'validate_symbol',
    'validate_alert_type',
    'validate_alert_condition',
    'get_alert_description'
]
