from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

from .models import Organization, DataSource, RawIngestion, NormalizedRow, ApprovalLog
from .serializers import (
    OrganizationSerializer, DataSourceSerializer, RawIngestionSerializer,
    NormalizedRowSerializer, ApprovalLogSerializer
)
from .parsers.sap_parser import SAPParser
from .parsers.utility_parser import UtilityParser
from .parsers.travel_parser import TravelParser


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class DataSourceViewSet(viewsets.ModelViewSet):
    serializer_class = DataSourceSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if org_id:
            return DataSource.objects.filter(org_id=org_id)
        return DataSource.objects.all()


class RawIngestionViewSet(viewsets.ModelViewSet):
    serializer_class = RawIngestionSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if org_id:
            return RawIngestion.objects.filter(org_id=org_id)
        return RawIngestion.objects.all()
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload and parse a file"""
        org_id = request.data.get('org_id')
        data_source_id = request.data.get('data_source_id')
        file = request.FILES.get('file')
        
        if not org_id or not data_source_id or not file:
            return Response(
                {'error': 'Missing org_id, data_source_id, or file'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            org = Organization.objects.get(id=org_id)
            data_source = DataSource.objects.get(id=data_source_id, org=org)
        except (Organization.DoesNotExist, DataSource.DoesNotExist):
            return Response(
                {'error': 'Organization or DataSource not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Read file content
        file_content = file.read()
        file_name = file.name
        
        # Parse based on source type
        parser = self._get_parser(data_source.source_type)
        if not parser:
            return Response(
                {'error': f'No parser available for {data_source.source_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            parsed_rows, parse_errors = parser.parse(file_content)
        except Exception as e:
            # Log the full error server-side, but don't expose to client
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Parse error: {str(e)}', exc_info=True)
            return Response(
                {'error': 'Failed to parse file. Please check the file format and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create RawIngestion record
        raw_ingestion = RawIngestion.objects.create(
            org=org,
            data_source=data_source,
            file_name=file_name,
            raw_data=parsed_rows,
            parsing_status='SUCCESS' if not parse_errors else 'SUCCESS',
            error_message=str(parse_errors) if parse_errors else None,
            row_count=len(parsed_rows)
        )
        
        # Create NormalizedRow records
        for parsed_row in parsed_rows:
            NormalizedRow.objects.create(
                org=org,
                data_source=data_source,
                raw_ingestion=raw_ingestion,
                source_row_id=parsed_row.get('source_row_id', f"row_{raw_ingestion.id}"),
                data_type=parsed_row.get('data_type', 'UNKNOWN'),
                data=parsed_row,
                scope=parsed_row.get('scope'),
                unit_normalized=parsed_row.get('unit_normalized'),
                amount_normalized=parsed_row.get('amount_normalized'),
                currency=parsed_row.get('currency'),
                location=parsed_row.get('location'),
                date=parsed_row.get('date'),
                flagged=parsed_row.get('flagged', False),
                flag_reason=parsed_row.get('flag_reason'),
            )
        
        serializer = RawIngestionSerializer(raw_ingestion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _get_parser(self, source_type):
        """Get appropriate parser for source type"""
        if source_type.startswith('SAP'):
            return SAPParser()
        elif source_type.startswith('UTILITY'):
            return UtilityParser()
        elif source_type.startswith('TRAVEL'):
            return TravelParser()
        return None


class NormalizedRowViewSet(viewsets.ModelViewSet):
    serializer_class = NormalizedRowSerializer
    
    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if not org_id:
            return NormalizedRow.objects.none()
        
        queryset = NormalizedRow.objects.filter(org_id=org_id)
        
        # Filtering
        data_type = self.request.query_params.get('data_type')
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        
        flagged = self.request.query_params.get('flagged')
        if flagged is not None:
            flagged = flagged.lower() == 'true'
            queryset = queryset.filter(flagged=flagged)
        
        approved = self.request.query_params.get('approved')
        if approved is not None:
            approved = approved.lower() == 'true'
            queryset = queryset.filter(approved_by__isnull=not approved)
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a normalized row"""
        row = self.get_object()
        row.approved_at = timezone.now()
        row.approved_by = request.user
        row.save()
        
        ApprovalLog.objects.create(
            org=row.org,
            normalized_row=row,
            action='APPROVED',
            user=request.user,
            notes=request.data.get('notes', '')
        )
        
        serializer = self.get_serializer(row)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Flag a row as suspicious"""
        row = self.get_object()
        row.flagged = True
        row.flag_reason = request.data.get('reason', 'Flagged for review')
        row.save()
        
        ApprovalLog.objects.create(
            org=row.org,
            normalized_row=row,
            action='FLAGGED',
            user=request.user,
            notes=request.data.get('notes', '')
        )
        
        serializer = self.get_serializer(row)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unflag(self, request, pk=None):
        """Remove flag from a row"""
        row = self.get_object()
        row.flagged = False
        row.flag_reason = None
        row.save()
        
        ApprovalLog.objects.create(
            org=row.org,
            normalized_row=row,
            action='UNFLAGGED',
            user=request.user,
            notes=request.data.get('notes', '')
        )
        
        serializer = self.get_serializer(row)
        return Response(serializer.data)


class ApprovalLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApprovalLogSerializer
    
    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if not org_id:
            return ApprovalLog.objects.none()
        
        queryset = ApprovalLog.objects.filter(org_id=org_id)
        
        # Optional filtering
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        days = self.request.query_params.get('days', 30)
        start_date = timezone.now() - timedelta(days=int(days))
        queryset = queryset.filter(timestamp__gte=start_date)
        
        return queryset


class DashboardView(viewsets.ViewSet):
    """Dashboard statistics"""
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        org_id = request.query_params.get('org_id')
        if not org_id:
            return Response(
                {'error': 'org_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        rows = NormalizedRow.objects.filter(org=org)
        
        stats = {
            'total_rows': rows.count(),
            'approved_rows': rows.filter(approved_by__isnull=False).count(),
            'flagged_rows': rows.filter(flagged=True).count(),
            'pending_rows': rows.filter(approved_by__isnull=True, flagged=False).count(),
            'by_data_type': dict(
                rows.values('data_type').annotate(count=Count('id')).values_list('data_type', 'count')
            ),
            'by_scope': dict(
                rows.filter(scope__isnull=False).values('scope').annotate(count=Count('id')).values_list('scope', 'count')
            ),
            'total_amount': sum([r.amount_normalized or 0 for r in rows]),
            'recent_uploads': RawIngestion.objects.filter(org=org).count(),
        }
        
        return Response(stats)
