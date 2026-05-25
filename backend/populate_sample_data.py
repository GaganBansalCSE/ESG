#!/usr/bin/env python
"""
Script to populate database with sample data for testing
Run with: python manage.py shell < populate_sample_data.py
"""
from core.models import Organization, DataSource, RawIngestion, NormalizedRow
from core.parsers.sap_parser import SAPParser
from core.parsers.utility_parser import UtilityParser
from core.parsers.travel_parser import TravelParser
import json
import os

def populate_sample_data():
    print("Creating sample organization...")
    org, created = Organization.objects.get_or_create(
        name='Acme Corporation',
        defaults={'name': 'Acme Corporation'}
    )
    if created:
        print(f"✓ Created organization: {org.name}")
    else:
        print(f"✓ Organization already exists: {org.name}")

    # Create data sources
    print("\nCreating data sources...")
    data_sources = [
        ('SAP_FUEL', 'SAP Fuel Data'),
        ('UTILITY_ELECTRICITY', 'Utility Electricity Data'),
        ('TRAVEL_FLIGHTS', 'Corporate Travel'),
    ]
    
    ds_objects = {}
    for source_type, name in data_sources:
        ds, created = DataSource.objects.get_or_create(
            org=org,
            source_type=source_type,
            defaults={
                'name': name,
                'config': {}
            }
        )
        ds_objects[source_type] = ds
        if created:
            print(f"✓ Created data source: {name}")

    # Load and parse sample data
    sample_data_dir = os.path.join(os.path.dirname(__file__), 'sample_data')
    
    print("\n" + "="*50)
    print("Parsing SAP Fuel Data...")
    print("="*50)
    sap_file = os.path.join(sample_data_dir, 'sap_fuel.csv')
    if os.path.exists(sap_file):
        with open(sap_file, 'r') as f:
            sap_content = f.read()
        
        parser = SAPParser()
        rows, errors = parser.parse(sap_content)
        
        if errors:
            print(f"⚠ Parsing errors: {errors}")
        
        raw_ingestion = RawIngestion.objects.create(
            org=org,
            data_source=ds_objects['SAP_FUEL'],
            file_name='sap_fuel.csv',
            raw_data=rows,
            parsing_status='SUCCESS',
            error_message=str(errors) if errors else None,
            row_count=len(rows)
        )
        print(f"✓ Created RawIngestion with {len(rows)} rows")
        
        for row in rows:
            NormalizedRow.objects.create(
                org=org,
                data_source=ds_objects['SAP_FUEL'],
                raw_ingestion=raw_ingestion,
                source_row_id=row.get('source_row_id'),
                data_type=row.get('data_type'),
                data=row,
                scope=row.get('scope'),
                unit_normalized=row.get('unit_normalized'),
                amount_normalized=row.get('amount_normalized'),
                currency=row.get('currency'),
                location=row.get('location'),
                date=row.get('date'),
                flagged=row.get('flagged', False),
                flag_reason=row.get('flag_reason'),
            )
        print(f"✓ Created {len(rows)} NormalizedRows")

    print("\n" + "="*50)
    print("Parsing Utility Electricity Data...")
    print("="*50)
    utility_file = os.path.join(sample_data_dir, 'utility_electricity.csv')
    if os.path.exists(utility_file):
        with open(utility_file, 'r') as f:
            utility_content = f.read()
        
        parser = UtilityParser()
        rows, errors = parser.parse(utility_content)
        
        if errors:
            print(f"⚠ Utility parsing had issues (expected in sample data)")
        
        raw_ingestion = RawIngestion.objects.create(
            org=org,
            data_source=ds_objects['UTILITY_ELECTRICITY'],
            file_name='utility_electricity.csv',
            raw_data=rows,
            parsing_status='SUCCESS',
            error_message=str(errors) if errors else None,
            row_count=len(rows)
        )
        print(f"✓ Created RawIngestion with {len(rows)} rows")
        
        for row in rows:
            NormalizedRow.objects.create(
                org=org,
                data_source=ds_objects['UTILITY_ELECTRICITY'],
                raw_ingestion=raw_ingestion,
                source_row_id=row.get('source_row_id'),
                data_type=row.get('data_type'),
                data=row,
                scope=row.get('scope'),
                unit_normalized=row.get('unit_normalized'),
                amount_normalized=row.get('amount_normalized'),
                currency=row.get('currency'),
                location=row.get('location'),
                date=row.get('date'),
                flagged=row.get('flagged', False),
                flag_reason=row.get('flag_reason'),
            )
        print(f"✓ Created {len(rows)} NormalizedRows")

    print("\n" + "="*50)
    print("Parsing Travel Data...")
    print("="*50)
    travel_file = os.path.join(sample_data_dir, 'travel_expenses.json')
    if os.path.exists(travel_file):
        with open(travel_file, 'r') as f:
            travel_content = f.read()
        
        parser = TravelParser()
        rows, errors = parser.parse(travel_content)
        
        if errors:
            print(f"⚠ Travel parsing had issues (expected in sample data)")
        
        raw_ingestion = RawIngestion.objects.create(
            org=org,
            data_source=ds_objects['TRAVEL_FLIGHTS'],
            file_name='travel_expenses.json',
            raw_data=rows,
            parsing_status='SUCCESS',
            error_message=str(errors) if errors else None,
            row_count=len(rows)
        )
        print(f"✓ Created RawIngestion with {len(rows)} rows")
        
        for row in rows:
            NormalizedRow.objects.create(
                org=org,
                data_source=ds_objects['TRAVEL_FLIGHTS'],
                raw_ingestion=raw_ingestion,
                source_row_id=row.get('source_row_id'),
                data_type=row.get('data_type'),
                data=row,
                scope=row.get('scope'),
                unit_normalized=row.get('unit_normalized'),
                amount_normalized=row.get('amount_normalized'),
                currency=row.get('currency'),
                location=row.get('location'),
                date=row.get('date'),
                flagged=row.get('flagged', False),
                flag_reason=row.get('flag_reason'),
            )
        print(f"✓ Created {len(rows)} NormalizedRows")

    print("\n" + "="*50)
    print("✓ Sample data population complete!")
    print("="*50)

if __name__ == '__main__':
    populate_sample_data()
