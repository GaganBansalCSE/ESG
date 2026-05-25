"""Travel Parser - handles corporate travel data (Concur/Navan-like JSON format)"""
import json
from .validators import validate_date, validate_currency, validate_amount


class TravelParser:
    """Parse travel JSON data with segment extraction and missing data detection"""
    
    SEGMENT_TYPES = {
        'AIRFR': 'Flight',
        'HOTEL': 'Hotel',
        'TAXIF': 'Ground Transport',
        'RAILF': 'Train',
        'CARHIRE': 'Car Rental',
    }
    
    def parse(self, file_content, encoding='utf-8'):
        """
        Parse travel JSON file
        Returns: (rows, errors)
        - rows: list of normalized dicts
        - errors: list of error dicts
        """
        rows = []
        errors = []
        
        try:
            if isinstance(file_content, bytes):
                file_content = file_content.decode(encoding)
            
            data = json.loads(file_content)
            
            # Handle both list and dict formats
            expenses = data if isinstance(data, list) else data.get('expenses', [])
            
            for exp_idx, expense in enumerate(expenses, start=1):
                try:
                    # Extract segments from expense
                    segments = expense.get('segments', [])
                    if not segments:
                        segments = [expense]  # Single segment expense
                    
                    for seg_idx, segment in enumerate(segments, start=1):
                        parsed = self._parse_segment(segment, expense, exp_idx, seg_idx)
                        rows.append(parsed)
                
                except Exception as e:
                    errors.append({
                        'expense_idx': exp_idx,
                        'error': str(e),
                        'data': str(expense)[:200]
                    })
            
            return rows, errors
        
        except json.JSONDecodeError as e:
            return [], [{'error': f'Invalid JSON format: {str(e)}'}]
        except Exception as e:
            return [], [{'error': f'Failed to parse travel data: {str(e)}'}]
    
    def _parse_segment(self, segment, expense, exp_idx, seg_idx):
        """Parse a single travel segment"""
        
        segment_type_code = segment.get('type', 'UNKNOWN')
        segment_type = self.SEGMENT_TYPES.get(segment_type_code, segment_type_code)
        
        # Extract dates
        start_date, start_invalid = validate_date(segment.get('start_date', ''))
        end_date, end_invalid = validate_date(segment.get('end_date', ''))
        
        # Extract cost
        cost, cost_invalid = validate_amount(segment.get('cost', segment.get('amount', '')))
        currency, currency_invalid = validate_currency(
            segment.get('currency', expense.get('currency', 'USD'))
        )
        
        # Extract distance (if available)
        distance = segment.get('distance', None)
        if distance:
            try:
                distance = float(distance)
            except (ValueError, TypeError):
                distance = None
        
        # Extract locations
        origin = segment.get('origin', segment.get('from', ''))
        destination = segment.get('destination', segment.get('to', ''))
        location = f"{origin} → {destination}" if origin and destination else origin or destination or ''
        
        # Detect missing or ambiguous data
        flagged = False
        flag_reasons = []
        
        if start_invalid or end_invalid:
            flagged = True
            flag_reasons.append('Invalid date format')
        
        if cost_invalid or currency_invalid:
            flagged = True
            if cost_invalid:
                flag_reasons.append('Invalid cost format')
            if currency_invalid:
                flag_reasons.append(f'Unknown currency: {segment.get("currency")}')
        
        if segment_type_code == 'AIRFR':
            # Check for missing cabin class
            cabin_class = segment.get('cabin_class', segment.get('class_of_service', '')).strip()
            if not cabin_class:
                flagged = True
                flag_reasons.append('Missing cabin class (affects emissions)')
            
            # Check for missing distance
            if not distance:
                flagged = True
                flag_reasons.append('Missing distance (calculated from origin/destination)')
            
            # Check for round-trip indication
            is_round_trip = segment.get('is_round_trip', False)
            if is_round_trip and not distance:
                flag_reasons = [f.replace('(calculated from origin/destination)', '(x2 for round-trip)') for f in flag_reasons]
        
        if segment_type_code == 'HOTEL':
            # Check for missing location
            hotel_location = segment.get('city', segment.get('location', ''))
            if not hotel_location:
                flagged = True
                flag_reasons.append('Missing hotel location')
            
            # Check for stay duration
            nights = segment.get('nights', 0)
            if nights == 0 and start_date and end_date:
                from datetime import datetime
                nights = (end_date - start_date).days
            if nights == 0:
                flagged = True
                flag_reasons.append('Unable to determine hotel stay duration')
        
        if not location and segment_type_code in ['AIRFR', 'RAILF']:
            flagged = True
            flag_reasons.append('Missing origin/destination locations')
        
        # Determine scope (Scope 3 for travel)
        scope = 3
        
        return {
            'source_row_id': f"travel_{exp_idx}_{seg_idx}",
            'data_type': 'TRAVEL',
            'expense_id': expense.get('id', f"exp_{exp_idx}"),
            'segment_type': segment_type,
            'segment_type_code': segment_type_code,
            'date': start_date,
            'start_date': start_date,
            'end_date': end_date,
            'origin': origin,
            'destination': destination,
            'location': location,
            'distance': distance,
            'cost': cost,
            'amount_normalized': cost,
            'currency': currency,
            'cabin_class': segment.get('cabin_class', segment.get('class_of_service', '')),
            'is_round_trip': segment.get('is_round_trip', False),
            'hotel_location': segment.get('city', segment.get('location', '')),
            'nights': segment.get('nights', 0),
            'scope': scope,
            'flagged': flagged,
            'flag_reason': ' | '.join(flag_reasons) if flag_reasons else None,
            'employee_id': expense.get('employee_id', ''),
            'department': expense.get('department', ''),
        }
