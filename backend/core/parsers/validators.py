"""Validators for parsed data"""
import re


def validate_unit(unit):
    """Validate and normalize unit strings"""
    unit_lower = str(unit).strip().lower()
    
    # Fuel/Volume units
    if unit_lower in ['l', 'liter', 'litre', 'l.', 'ltr']:
        return 'L', False
    if unit_lower in ['m³', 'm3', 'cbm', 'cubic meter']:
        return 'm³', False
    if unit_lower in ['kg', 'kilogram', 'kgs']:
        return 'kg', False
    if unit_lower in ['t', 'tonne', 'ton', 'mt']:
        return 'kg', False  # Convert tonnes to kg
    
    # Electricity units
    if unit_lower in ['kwh', 'kw/h', 'kwh.']:
        return 'kWh', False
    if unit_lower in ['mwh', 'mw/h', 'mwh.']:
        return 'kWh', False  # Convert MWh to kWh
    if unit_lower in ['wh', 'w/h']:
        return 'kWh', False  # Convert Wh to kWh
    
    return unit, True  # Return original and flag as unknown


def validate_amount(value):
    """Validate and convert amount to float"""
    try:
        if isinstance(value, (int, float)):
            return float(value), False
        
        # Handle string amounts with decimal separators (comma or dot)
        value_str = str(value).strip()
        
        # Common German format: 1.000,50 -> convert to 1000.50
        if ',' in value_str and '.' in value_str:
            # Determine which is decimal separator
            if value_str.rfind(',') > value_str.rfind('.'):
                value_str = value_str.replace('.', '').replace(',', '.')
            else:
                value_str = value_str.replace(',', '')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        amount = float(value_str)
        return amount, False
    except (ValueError, TypeError):
        return None, True


def validate_date(date_value):
    """Attempt to parse various date formats"""
    from datetime import datetime
    
    if date_value is None:
        return None, True
    
    date_str = str(date_value).strip()
    
    # Try common formats
    formats = [
        '%Y-%m-%d',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date(), False
        except ValueError:
            continue
    
    return None, True


def validate_currency(currency):
    """Validate currency code"""
    if currency is None:
        return 'USD', True  # Default to USD if not provided
    
    currency_upper = str(currency).strip().upper()
    
    valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY', 'INR']
    if currency_upper in valid_currencies:
        return currency_upper, False
    
    return currency_upper, True  # Flag unknown currencies
