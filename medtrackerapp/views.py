from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .models import Medication, DoseLog, Note
from .serializers import MedicationSerializer, DoseLogSerializer, NoteSerializer
from rest_framework.filters import SearchFilter

def _get_required_positive_int_query_param(request, name: str) -> int:
    """Parse a required positive integer query parameter.

    Raises:
        ValueError: If the parameter is missing, not an integer, or <= 0.
    """
    raw_value = request.query_params.get(name)
    if raw_value is None:
        raise ValueError(f"Query parameter '{name}' is required.")

    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Query parameter '{name}' must be a positive integer.") from exc

    if value <= 0:
        raise ValueError(f"Query parameter '{name}' must be a positive integer.")

    return value

class MedicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing medications.

    Provides standard CRUD operations via the Django REST Framework
    `ModelViewSet`, as well as a custom action for retrieving
    additional information from an external API (OpenFDA).

    Endpoints:
        - GET /medications/ — list all medications
        - POST /medications/ — create a     new medication
        - GET /medications/{id}/ — retrieve a specific medication
        - PUT/PATCH /medications/{id}/ — update a medication
        - DELETE /medications/{id}/ — delete a medication
        - GET /medications/{id}/info/ — fetch external drug info from OpenFDA
        - GET /medications/{id}/expected-doses/?days=X — expected doses over X days
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer

    @action(detail=True, methods=["get"], url_path="info")
    def get_external_info(self, request, pk=None):
        """
        Retrieve external drug information from the OpenFDA API.

        Calls the `Medication.fetch_external_info()` method, which
        delegates to the `DrugInfoService` for API access.

        Args:
            request (Request): The current HTTP request.
            pk (int): Primary key of the medication record.

        Returns:
            Response:
                - 200 OK: External API data returned successfully.
                - 502 BAD GATEWAY: If the external API request failed.

        Example:
            GET /medications/1/info/
        """
        medication = self.get_object()
        data = medication.fetch_external_info()

        if isinstance(data, dict) and data.get("error"):
            return Response(data, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="expected-doses")
    def expected_doses(self, request, pk=None):
        """Return the expected number of doses over a given number of days.

        Endpoint:
            GET /api/medications/<id>/expected-doses/?days=X

        Query parameters:
            days (required): Positive integer.

        Responses:
            200: {medication_id, days, expected_doses}
            400: If 'days' is missing/invalid or model computation raises ValueError.
        """
        try:
            days = _get_required_positive_int_query_param(request, "days")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        medication = self.get_object()

        try:
            expected_dose_count = medication.expected_doses(days)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "medication_id": medication.id,
                "days": days,
                "expected_doses": expected_dose_count,
            },
            status=status.HTTP_200_OK,
        )


class DoseLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing dose logs.

    A DoseLog represents an event where a medication dose was either
    taken or missed. This viewset provides standard CRUD operations
    and a custom filtering action by date range.

    Endpoints:
        - GET /logs/ — list all dose logs
        - POST /logs/ — create a new dose log
        - GET /logs/{id}/ — retrieve a specific log
        - PUT/PATCH /logs/{id}/ — update a dose log
        - DELETE /logs/{id}/ — delete a dose log
        - GET /logs/filter/?start=YYYY-MM-DD&end=YYYY-MM-DD —
          filter logs within a date range
    """
    queryset = DoseLog.objects.all()
    serializer_class = DoseLogSerializer

    @action(detail=False, methods=["get"], url_path="filter")
    def filter_by_date(self, request):
        """
        Retrieve all dose logs within a given date range.

        Query Parameters:
            - start (YYYY-MM-DD): Start date of the range (inclusive).
            - end (YYYY-MM-DD): End date of the range (inclusive).

        Returns:
            Response:
                - 200 OK: A list of dose logs between the two dates.
                - 400 BAD REQUEST: If start or end parameters are missing or invalid.

        Example:
            GET /logs/filter/?start=2025-11-01&end=2025-11-07
        """
        start = parse_date(request.query_params.get("start"))
        end = parse_date(request.query_params.get("end"))

        if not start or not end:
            return Response(
                {"error": "Both 'start' and 'end' query parameters are required and must be valid dates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = self.get_queryset().filter(
            taken_at__date__gte=start,
            taken_at__date__lte=end
        ).order_by("taken_at")

        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class NoteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """API endpoint for listing, retrieving, creating, and deleting notes.

    Updating existing notes is intentionally not supported.

    Endpoints:
        - GET /notes/ — list all notes
        - POST /notes/ — create a new note
        - GET /notes/{id}/ — retrieve a specific note
        - DELETE /notes/{id}/ — delete a specific note
    """
    filter_backends = (SearchFilter,)
    search_fields = ['medication__name']
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
