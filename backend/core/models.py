from django.db import models
from django.contrib.auth.models import User
import json

class Organization(models.Model):
    """Multi-tenant organization model"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class DataSource(models.Model):
    """Data source configuration"""
    SOURCE_TYPES = [
        ('SAP_FUEL', 'SAP Fuel Data'),
        ('SAP_PROCUREMENT', 'SAP Procurement Data'),
        ('UTILITY_ELECTRICITY', 'Utility Electricity Data'),
        ('TRAVEL_FLIGHTS', 'Travel - Flights'),
        ('TRAVEL_HOTELS', 'Travel - Hotels'),
        ('TRAVEL_GROUND', 'Travel - Ground Transport'),
    ]

    id = models.AutoField(primary_key=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='data_sources')
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    name = models.CharField(max_length=255)
    config = models.JSONField(default=dict)  # For storing credentials/settings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.org.name} - {self.get_source_type_display()}"

    class Meta:
        ordering = ['-created_at']


class RawIngestion(models.Model):
    """Raw data upload/ingestion"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARSING', 'Parsing'),
        ('SUCCESS', 'Success'),
        ('ERROR', 'Error'),
    ]

    id = models.AutoField(primary_key=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='raw_ingestions')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='raw_ingestions')
    upload_date = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    raw_data = models.JSONField()  # Stores parsed CSV/JSON as list of dicts
    parsing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(null=True, blank=True)
    row_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.org.name} - {self.data_source.name} - {self.upload_date}"

    class Meta:
        ordering = ['-upload_date']


class NormalizedRow(models.Model):
    """Parsed and normalized data, ready for review"""
    DATA_TYPES = [
        ('SAP', 'SAP Data'),
        ('UTILITY', 'Utility Data'),
        ('TRAVEL', 'Travel Data'),
    ]
    SCOPE_CHOICES = [
        (1, 'Scope 1'),
        (2, 'Scope 2'),
        (3, 'Scope 3'),
    ]

    id = models.AutoField(primary_key=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='normalized_rows')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='normalized_rows')
    raw_ingestion = models.ForeignKey(RawIngestion, on_delete=models.CASCADE, related_name='normalized_rows')
    source_row_id = models.CharField(max_length=255)  # Reference to original row
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    data = models.JSONField()  # Raw normalized data

    # Normalized fields for querying
    scope = models.IntegerField(choices=SCOPE_CHOICES, null=True, blank=True)
    unit_normalized = models.CharField(max_length=50, null=True, blank=True)  # L, kg, kWh, etc.
    amount_normalized = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)  # USD, EUR, etc.
    location = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    # Flagging and approval
    flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_rows')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.org.name} - {self.data_type} - {self.date}"

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['org', 'data_type', 'date']),
            models.Index(fields=['org', 'flagged']),
            models.Index(fields=['approved_by']),
        ]


class ApprovalLog(models.Model):
    """Audit trail for approvals and rejections"""
    ACTION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged'),
        ('UNFLAGGED', 'Unflagged'),
    ]

    id = models.AutoField(primary_key=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='approval_logs')
    normalized_row = models.ForeignKey(NormalizedRow, on_delete=models.CASCADE, related_name='approval_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['org', 'timestamp']),
            models.Index(fields=['normalized_row']),
        ]
