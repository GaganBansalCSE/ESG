"""SAP Parser - handles SAP fuel and procurement data"""
import csv
from io import StringIO
from .validators import validate_unit, validate_amount, validate_date, validate_currency


class SAPParser:
    """Parse SAP CSV data with German headers and unit normalization"""
    
    GERMAN_HEADER_MAP = {
        'matnr': 'material_number',
        'materialwert': 'material_number',
        'werks': 'plant',
        'plant': 'plant',
        'menge': 'quantity',
        'qty': 'quantity',
        'meins': 'unit',
        'unit': 'unit',
        'budat': 'date',
        'posting_date': 'date',
        'netpr': 'price',
        'price': 'price',
        'waers': 'currency',
        'currency': 'currency',
        'kostl': 'cost_center',
        'cost_center': 'cost_center',
        'ebeln': 'po_number',
        'po': 'po_number',
    }
    
    def parse(self, file_content, encoding='utf-8'):
        """
        Parse SAP CSV file
        Returns: (rows, errors)
        - rows: list of normalized dicts
        - errors: list of error dicts with row info
        """
        rows = []
        errors = []
        
        try:
            if isinstance(file_content, bytes):
                file_content = file_content.decode(encoding)
            
            reader = csv.DictReader(StringIO(file_content), delimiter=',')
            if not reader.fieldnames:
                return [], [{'error': 'Empty CSV file'}]
            
            # Normalize headers
            normalized_headers = self._normalize_headers(reader.fieldnames)
            seen_rows = set()
            
            for row_idx, row in enumerate(reader, start=1):
                try:
                    normalized_row = {}
                    for orig_key, norm_key in zip(reader.fieldnames, normalized_headers):
                        normalized_row[norm_key] = row.get(orig_key, '')
                    
                    parsed = self._parse_row(normalized_row, row_idx)
                    
                    # Check for duplicates
                    row_signature = (
                        parsed.get('material_number'),
                        parsed.get('plant'),
                        parsed.get('date'),
                        parsed.get('quantity')
                    )
                    
                    if row_signature in seen_rows:
                        errors.append({
                            'row_idx': row_idx,
                            'error': 'Duplicate row detected',
                            'signature': str(row_signature)
                        })
                        parsed['flagged'] = True
                        parsed['flag_reason'] = 'Possible duplicate row'
                    else:
                        seen_rows.add(row_signature)
                    
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
        """Convert German/variant headers to standard names"""
        normalized = []
        for header in headers:
            header_lower = header.strip().lower()
            normalized.append(self.GERMAN_HEADER_MAP.get(header_lower, header_lower))
        return normalized
    
    def _parse_row(self, row, row_idx):
        """Parse a single SAP row"""
        
        quantity, qty_invalid = validate_amount(row.get('quantity', ''))
        unit, unit_invalid = validate_unit(row.get('unit', ''))
        
        # Convert tonnes to kg if needed
        if unit == 'kg' and row.get('unit', '').lower() in ['t', 'tonne', 'ton', 'mt']:
            quantity = quantity * 1000 if quantity else None
        
        # Convert MWh to kWh if needed
        if unit == 'kWh' and row.get('unit', '').lower() in ['mwh', 'mw/h', 'mwh.']:
            quantity = quantity * 1000 if quantity else None
        
        date, date_invalid = validate_date(row.get('date', ''))
        price, price_invalid = validate_amount(row.get('price', ''))
        currency, currency_invalid = validate_currency(row.get('currency', 'USD'))
        
        flagged = qty_invalid or unit_invalid or date_invalid or price_invalid or currency_invalid
        flag_reasons = []
        if qty_invalid:
            flag_reasons.append('Invalid quantity format')
        if unit_invalid:
            flag_reasons.append(f'Unknown unit: {row.get("unit")}')
        if date_invalid:
            flag_reasons.append('Invalid date format')
        if price_invalid:
            flag_reasons.append('Invalid price format')
        if currency_invalid:
            flag_reasons.append(f'Unknown currency: {row.get("currency")}')
        
        return {
            'source_row_id': f"sap_{row_idx}",
            'data_type': 'SAP',
            'material_number': row.get('material_number', ''),
            'plant': row.get('plant', ''),
            'quantity': quantity,
            'unit_normalized': unit,
            'amount_normalized': price,
            'currency': currency,
            'date': date,
            'cost_center': row.get('cost_center', ''),
            'po_number': row.get('po_number', ''),
            'scope': 1,  # SAP fuel/procurement typically Scope 1
            'flagged': flagged,
            'flag_reason': ' | '.join(flag_reasons) if flag_reasons else None,
            'location': row.get('plant', ''),
        }
