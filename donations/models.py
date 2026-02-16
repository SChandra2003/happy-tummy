
from django.db import models
from django.contrib.auth.models import User
# NGO can request food from restaurants
class NGOFoodRequest(models.Model):
    ngo = models.ForeignKey('NGOProfile', on_delete=models.CASCADE)
    food_type = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)
    accepted_by = models.ForeignKey('RestaurantProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='accepted_ngo_requests')

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.ngo.name} requests {self.quantity} {self.food_type}"

# ===========================================
# USER PROFILES & ROLES
# ===========================================

class RestaurantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, unique=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100)  # keep
    pincode = models.CharField(max_length=10, blank=True, null=True)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.business_name


class VolunteerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    area = models.CharField(max_length=150)
    is_available = models.BooleanField(default=True)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to='volunteer_photos/', blank=True, null=True)
    aadhar_card = models.CharField(max_length=12, unique=True)
    aadhar_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class NGOProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    ROLE_CHOICES = (
        ("restaurant", "Restaurant"),
        ("volunteer", "Volunteer"),
        ("ngo", "NGO"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} — {self.role}"


# ===========================================
# OPERATIONAL MODELS
# ===========================================

class SurplusFoodRequest(models.Model):
    # link to RestaurantProfile, not old Restaurant
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.CASCADE)
    food_type = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_picked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.restaurant.business_name} - {self.quantity} meals"



class PickupTask(models.Model):
    # For surplus food: request is SurplusFoodRequest, ngo_request is null
    # For NGO food request: ngo_request is NGOFoodRequest, request is null
    request = models.ForeignKey(SurplusFoodRequest, on_delete=models.CASCADE, null=True, blank=True)
    ngo_request = models.ForeignKey(NGOFoodRequest, on_delete=models.CASCADE, null=True, blank=True)
    assigned_to = models.ForeignKey(VolunteerProfile, on_delete=models.SET_NULL, null=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-assigned_at"]

    def __str__(self):
        if self.request:
            return f"Pickup for: {self.request.restaurant.business_name} (Surplus)"
        elif self.ngo_request:
            return f"Pickup for: {self.ngo_request.accepted_by.business_name if self.ngo_request.accepted_by else 'Unassigned'} (NGO Request)"
        return "Pickup Task"

    @property
    def source_address(self):
        if self.request:
            return self.request.restaurant.address
        elif self.ngo_request and self.ngo_request.accepted_by:
            return self.ngo_request.accepted_by.address
        return "-"

    @property
    def destination_address(self):
        if self.request:
            # Surplus food always goes to the NGO that accepted
            return getattr(self.request, 'accepted_by_ngo_address', '-')
        elif self.ngo_request and self.ngo_request.ngo:
            return self.ngo_request.ngo.address
        return "-"


class Donation(models.Model):
    restaurant_name = models.CharField(max_length=200)
    food_type = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField()
    city = models.CharField(max_length=120)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.restaurant_name} - {self.quantity} meals"
