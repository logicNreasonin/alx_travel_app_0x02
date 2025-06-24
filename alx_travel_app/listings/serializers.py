from rest_framework import serializers
from .models import Listing, Booking

class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__' # Or specify fields: ['id', 'name', 'description', 'address', 'price_per_night', 'created_at', 'updated_at']

class BookingSerializer(serializers.ModelSerializer):
    # You might want to show some listing details in the booking response
    # listing_name = serializers.CharField(source='listing.name', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__' # Or specify fields: ['id', 'listing', 'guest_name', 'check_in_date', 'check_out_date', 'number_of_guests', 'created_at', 'updated_at']
        # If 'listing' should be represented by its ID for POST/PUT but more info for GET,
        # you could use depth or a nested serializer. For simplicity, '__all__' will use PKs for relations.

    def validate(self, data):
        """
        Check that check_out_date is after check_in_date.
        """
        if 'check_in_date' in data and 'check_out_date' in data:
            if data['check_out_date'] <= data['check_in_date']:
                raise serializers.ValidationError("Check-out date must be after check-in date.")
        return data