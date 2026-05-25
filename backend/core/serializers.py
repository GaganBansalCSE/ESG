from rest_framework import serializers
from .models import Organization, DataSource, RawIngestion, NormalizedRow, ApprovalLog


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'org', 'source_type', 'name', 'config', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RawIngestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawIngestion
        fields = ['id', 'org', 'data_source', 'upload_date', 'file_name', 'raw_data', 
                  'parsing_status', 'error_message', 'row_count']
        read_only_fields = ['id', 'upload_date', 'parsing_status', 'error_message', 'row_count']


class NormalizedRowSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = NormalizedRow
        fields = ['id', 'org', 'data_source', 'raw_ingestion', 'source_row_id', 'data_type', 
                  'data', 'scope', 'unit_normalized', 'amount_normalized', 'currency', 
                  'location', 'date', 'flagged', 'flag_reason', 'approved_at', 'approved_by',
                  'approved_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'approved_at', 'created_at', 'updated_at']


class ApprovalLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ApprovalLog
        fields = ['id', 'org', 'normalized_row', 'action', 'user', 'user_name', 'timestamp', 'notes']
        read_only_fields = ['id', 'timestamp']
