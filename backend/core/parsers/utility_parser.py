"""Utility Parser - handles electricity billing data"""
import csv
from io import StringIO
from .validators import validate_amount, validate_date, validate_currency


class UtilityParser:
    """Parse utility electricity CSV with billing period handling and deduplication"""
    
    HEADER_MAP = {
        'meter_id': 'meter_id',
        'meterid': 'meter_id',
        'meter': 'meter_id',
        'billing_period_start': 'billing_period_start',
        'period_start': 'billing_period_start',
        'start_date': 'billing_period_start',
        'from_date': 'billing_period_start',
        'billing_period_end': 'billing_period_end',
        'period_end': 'billing_period_end',
        'end_date': 'billing_period_end',
        'to_date': 'billing_period_end',
        'quantity': 'quantity',
        'qty': 'quantity',
        'usage': 'quantity',
        'consumption': 'quantity',
        'kwh': 'quantity',
        'mwh': 'quantity',
        'unit': 'unit',
        'cost': 'cost',
        'amount': 'cost',
        'price': 'cost',
        'currency': 'currency',
        'location': 'location',
        'site': 'location',
        'facility': 'location',
    }
    
    def parse(self, file_content, encoding='utf-8'):
        """
        Parse utility CSV file
        Returns: (rows, errors)
        - rows: list of normalized dicts (deduplicated)
        - errors: list of error dicts
        """
        rows = []
        errors = []
        seen_keys = {}  # Track deduplicated rows
        
        try:
            if isinstance(file_content, bytes):
                file_content = file_content.decode(encoding)
            
            reader = csv.DictReader(StringIO(file_content), delimiter=',')
            if not reader.fieldnames:
                return [], [{'error': 'Empty CSV file'}]
            
            # Normalize headers
            normalized_headers = self._normalize_headers(reader.fieldnames)
            
            for row_idx, row in enumerate(reader, start=1):
                try:
                    normalized_row = {}
                    for orig_key, norm_key in zip(reader.fieldnames, normalized_headers):
                        normalized_row[norm_key] = row.get(orig_key, '')
                    
                    parsed = self._parse_row(normalized_row, row_idx)
                    
                    # Dedup by (meter_id, billing_period_start, billing_period_end)
                    dedup_key = (
                        parsed.get('meter_id'),
                        str(parsed.get('billing_period_start')),
                        str(parsed.get('billing_period_end'))
                    )
                    
                    if dedup_key in seen_keys:
                        # This is a duplicate (e.g., billing correction)
                        prev_idx, prev_qty = seen_keys[dedup_key]
                        errors.append({
                            'row_idx': row_idx,
                            'error': 'Duplicate billing period detected',
                            'previous_row': prev_idx,
                            'note': 'This may be a billing correction. Review both rows.'
                        })
                        parsed['flagged'] = True
                        parsed['flag_reason'] = f'Duplicate billing period (first occurrence row {prev_idx})'
                    else:
                        seen_keys[dedup_key] = (row_idx, parsed.get('quantity'))
                    
                    rows.append(parsed)
                except Exception as e:
                    errors.append({
                        'row_idx': row_idx,
                        'error': str(e),
                        'row': row
                    })
            
            return rows, errors
        
        except Exception as e:
            return [], [{'error': f'Failed to parse CSV: {str(e)}'}]
    
    def _normalize_headers(self, headers):
        """Normalize header names"""
        normalized = []
        for header in headers:
            header_lower = header.strip().lower()
            normalized.append(self.HEADER_MAP.get(header_lower, header_lower))
        return normalized
    
    def _parse_row(self, row, row_idx):
        """Parse a single utility row"""
        
        meter_id = row.get('meter_id', '').strip()
        quantity, qty_invalid = validate_amount(row.get('quantity', ''))
        
        # Determine unit and normalize
        unit_str = row.get('unit', 'kWh').strip().lower()
        if unit_str in ['mwh', 'mw/h']:
            if quantity:
                quantity *= 1000  # Convert MWh to kWh
            unit = 'kWh'
            unit_invalid = False
        else:
            unit = 'kWh'
            unit_invalid = False
        
        cost, cost_invalid = validate_amount(row.get('cost', ''))
        currency, currency_invalid = validate_currency(row.get('currency', 'USD'))
        
        start_date, start_invalid = validate_date(row.get('billing_period_start', ''))
        end_date, end_invalid = validate_date(row.get('billing_period_end', ''))
        
        # Flag rows with issues
        flagged = qty_invalid or cost_invalid or currency_invalid or start_invalid or end_invalid or not meter_id
        flag_reasons = []
        
        if not meter_id:
            flag_reasons.append('Missing meter ID')
        if qty_invalid:
            flag_reasons.append('Invalid quantity format')
        if cost_invalid:
            flag_reasons.append('Invalid cost format')
        if currency_invalid:
            flag_reasons.append(f'Unknown currency: {row.get("currency")}')
        if start_invalid:
            flag_reasons.append('Invalid start date format')
        if end_invalid:
            flag_reasons.append('Invalid end date format')
        
        # Check if billing period aligns to calendar month
        billing_month_alignment = 'Yes'
        if start_date and end_date:
            # Simple check: if start is 1st of month and end is last day, it's aligned
            if start_date.day != 1:
                billing_month_alignment = 'No - starts mid-month'
            if end_date.month != (end_date.month if end_date.day == 1 else end_date.month):
                billing_month_alignment = 'No - ends mid-month'
        
        return {
            'source_row_id': f"utility_{row_idx}",
            'data_type': 'UTILITY',
            'meter_id': meter_id,
            'billing_period_start': start_date,
            'billing_period_end': end_date,
            'quantity': quantity,
            'unit_normalized': unit,
            'amount_normalized': cost,
            'currency': currency,
            'location': row.get('location', ''),
            'scope': 2,  # Utility electricity typically Scope 2
            'billing_month_alignment': billing_month_alignment,
            'flagged': flagged,
            'flag_reason': ' | '.join(flag_reasons) if flag_reasons else None,
            'date': start_date,  # Use start date for sorting
        }
