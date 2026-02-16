from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from donations.models import (
    RestaurantProfile,
    VolunteerProfile,
    NGOProfile,
    SurplusFoodRequest,
    PickupTask,
    NGOFoodRequest,
)
import requests
from django.db import models
from django.utils import timezone
import json
# ---------------------------
# RESTAURANT DASHBOARD
# ---------------------------
@login_required(login_url="/")
def restaurant_dashboard(request):
    try:
        profile = RestaurantProfile.objects.get(user=request.user)
    except RestaurantProfile.DoesNotExist:
        return render(request, "dashboard/restaurant_dashboard.html", {
            "profile": None,
            "error": "No restaurant profile found for this account. Please contact support or re-register."
        })

    # -------------------------------------------------
    # HANDLE POST REQUESTS
    # -------------------------------------------------
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_donation":
            donation = SurplusFoodRequest.objects.create(
                restaurant=profile,
                food_type=request.POST.get("food_type"),
                quantity=request.POST.get("quantity"),
            )
            return redirect("restaurant_dashboard")

        elif action == "update_profile":
            profile.business_name = request.POST.get("business_name")
            profile.contact_person = request.POST.get("contact_person")
            profile.phone = request.POST.get("phone")

            profile.state = request.POST.get("state")
            profile.district = request.POST.get("district")
            profile.city = request.POST.get("city")


            profile.pincode = request.POST.get("pincode")
            # Only assign taluka if it exists in the model
            if hasattr(profile, "taluka"):
                profile.taluka = request.POST.get("taluka")

            profile.address = request.POST.get("address")

            profile.save()
            return redirect("restaurant_dashboard")

        elif action == "accept_ngo_request":
            ngo_request_id = request.POST.get("ngo_request_id")
            try:
                ngo_request = NGOFoodRequest.objects.get(id=ngo_request_id, fulfilled=False, accepted_by__isnull=True)
                ngo_request.accepted_by = profile
                ngo_request.save()

                # Create PickupTask for this NGO request (restaurant -> NGO)
                PickupTask.objects.get_or_create(ngo_request=ngo_request)

                # Notify nearby volunteers (same city)
                city = profile.city
                nearby_volunteers = VolunteerProfile.objects.filter(area__icontains=city, is_available=True)
                for volunteer in nearby_volunteers:
                    # Placeholder for notification logic (email, SMS, app notification)
                    print(f"Notify volunteer {volunteer.full_name} ({volunteer.phone}) for delivery of NGO food request {ngo_request.id} in {city}")
            except NGOFoodRequest.DoesNotExist:
                pass
            return redirect("restaurant_dashboard")

    # -------------------------------------------------
    # GEOCODING (STRUCTURED — NO OCEAN)
    # -------------------------------------------------
    lat = lng = None

    try:
        params = {
            "street": profile.address,
            "city": profile.city,
            "state": profile.state,
            "postalcode": profile.pincode,
            "country": "India",
            "format": "json",
            "limit": 1,
        }

        res = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": "HappyTummy-App"},
            timeout=8,
        )

        data = res.json()
        print("GEOCODER RESPONSE:", data)

        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])

    except Exception as e:
        print("GEOCODING ERROR:", e)

    # -------------------------------------------------
    # FALLBACK (ONLY IF API FAILS)
    # -------------------------------------------------
    if not lat or not lng:
        lat, lng = 22.5726, 88.3639  # Kolkata

    # -------------------------------------------------
    # DASHBOARD DATA
    # -------------------------------------------------

    requests_qs = SurplusFoodRequest.objects.filter(restaurant=profile).order_by("-timestamp")
    recent_requests = requests_qs[:10]

    total_donations = requests_qs.count()
    pending_pickups = requests_qs.filter(is_picked=False).count()
    completed_pickups = requests_qs.filter(is_picked=True).count()

    # Show NGO food requests in the same city (including ones accepted by this restaurant)
    nearby_ngo_requests = NGOFoodRequest.objects.filter(
        ngo__city__iexact=profile.city
    ).filter(
        models.Q(accepted_by__isnull=True) | models.Q(accepted_by=profile)
    ).select_related('ngo', 'accepted_by')

    # -------------------------------------------------
    # RENDER
    # -------------------------------------------------
    return render(request, "dashboard/restaurant_dashboard.html", {
        "profile": profile,
        "requests": recent_requests,
        "total_donations": total_donations,
        "pending_pickups": pending_pickups,
        "completed_pickups": completed_pickups,
        "lat": lat,
        "lng": lng,
        "nearby_ngo_requests": nearby_ngo_requests,
    })

# ---------------------------
# VOLUNTEER DASHBOARD
# ---------------------------
@login_required(login_url="/")
def volunteer_dashboard(request):
    profile = VolunteerProfile.objects.get(user=request.user)

    if request.method == "POST" and request.POST.get("action") == "update_profile":
        profile.full_name = request.POST.get("full_name")
        profile.phone = request.POST.get("phone")
        profile.area = request.POST.get("area")
        profile.save()
        return redirect("volunteer_dashboard")


    my_tasks = PickupTask.objects.filter(assigned_to=profile)
    pending_count = my_tasks.filter(completed=False).count()
    completed_count = my_tasks.filter(completed=True).count()

    # Find available pickup tasks in volunteer's location (not yet assigned)
    volunteer_city = profile.area.split(',')[-1].strip() if ',' in profile.area else profile.area.strip()
    from datetime import timedelta
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Available SurplusFoodRequests (not picked, not expired, in city)
    from donations.models import SurplusFoodRequest, NGOFoodRequest
    print(f"[DEBUG] Volunteer city: '{volunteer_city}'")
    all_surplus = SurplusFoodRequest.objects.all()
    print(f"[DEBUG] All SurplusFoodRequest: {[{'id':s.id, 'city':s.restaurant.city, 'picked':s.is_picked, 'ts':s.timestamp} for s in all_surplus]}")
    available_requests = SurplusFoodRequest.objects.filter(
        is_picked=False,
        timestamp__gte=one_hour_ago,
        restaurant__city__iexact=volunteer_city
    )
    print(f"[DEBUG] Available SurplusFoodRequest for city '{volunteer_city}': {[{'id':s.id, 'city':s.restaurant.city, 'picked':s.is_picked, 'ts':s.timestamp} for s in available_requests]}")

    # Available PickupTasks (not assigned, not completed, not expired, in city)
    all_pickups = PickupTask.objects.filter(assigned_to=None, completed=False)
    print(f"[DEBUG] All unassigned PickupTasks: {[{'id':p.id, 'city':getattr(p.request.restaurant, 'city', None) if p.request else None, 'ts':getattr(p.request, 'timestamp', None) if p.request else None} for p in all_pickups]}")
    available_pickups = PickupTask.objects.filter(
        assigned_to=None,
        completed=False
    ).filter(
        (
            models.Q(request__restaurant__city__iexact=volunteer_city, request__timestamp__gte=one_hour_ago)
        ) |
        (
            models.Q(ngo_request__accepted_by__city__iexact=volunteer_city, ngo_request__timestamp__gte=one_hour_ago, ngo_request__fulfilled=False)
        )
    )
    print(f"[DEBUG] Available PickupTasks for city '{volunteer_city}': {[{'id':p.id, 'city':getattr(p.request.restaurant, 'city', None) if p.request else None, 'ts':getattr(p.request, 'timestamp', None) if p.request else None} for p in available_pickups]}")

    # Handle volunteer accepting a pickup
    if request.method == "POST" and request.POST.get("action") == "accept_pickup":
        pickup_id = request.POST.get("pickup_id")
        try:
            pickup = PickupTask.objects.get(id=pickup_id, assigned_to=None, completed=False)
            pickup.assigned_to = profile
            pickup.save()
        except PickupTask.DoesNotExist:
            pass
        return redirect("volunteer_dashboard")

    # Handle volunteer completing a pickup
    if request.method == "POST" and request.POST.get("action") == "complete_pickup":
        pickup_id = request.POST.get("pickup_id")
        try:
            pickup = PickupTask.objects.get(id=pickup_id, assigned_to=profile, completed=False)
            pickup.completed = True
            pickup.save()

            # If this pickup is for a SurplusFoodRequest, mark as delivered (transaction over)
            if pickup.request:
                # Optionally, mark as delivered in SurplusFoodRequest or log transaction
                pass
            # If this pickup is for an NGOFoodRequest, mark as fulfilled
            if pickup.ngo_request:
                pickup.ngo_request.fulfilled = True
                pickup.ngo_request.save()
        except PickupTask.DoesNotExist:
            pass
        return redirect("volunteer_dashboard")

    has_active_task = my_tasks.filter(completed=False).exists()

    return render(request, "dashboard/volunteer_dashboard.html", {
        "profile": profile,
        "tasks": my_tasks,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "available_pickups": available_pickups,
        "available_requests": available_requests,
        "volunteer_city": volunteer_city,
        "has_active_task": has_active_task,
    })


# ---------------------------
# NGO DASHBOARD
# ---------------------------
@login_required(login_url="/")
def ngo_dashboard(request):
    try:
        profile = NGOProfile.objects.get(user=request.user)
    except NGOProfile.DoesNotExist:
        return render(request, "dashboard/ngo_dashboard.html", {
            "profile": None,
            "error": "No NGO profile found for this account. Please contact support or re-register."
        })

    # Own food requests by this NGO
    from donations.models import NGOFoodRequest
    my_food_requests = NGOFoodRequest.objects.filter(ngo=profile).order_by('-timestamp')

    # -------------------------------------------------
    # HANDLE POST REQUESTS
    # -------------------------------------------------
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            profile.name = request.POST.get("name")
            profile.contact_person = request.POST.get("contact_person")
            profile.phone = request.POST.get("phone")
            profile.address = request.POST.get("address")
            profile.city = request.POST.get("city")

            profile.save()
            return redirect("ngo_dashboard")

        elif action == "accept_donation":
            donation_id = request.POST.get("donation_id")
            try:
                donation = SurplusFoodRequest.objects.get(id=donation_id, is_picked=False)
                donation.is_picked = True
                donation.save()

                # Create PickupTask for this surplus food (restaurant -> NGO)
                PickupTask.objects.get_or_create(request=donation)

                # Notify nearby volunteers (same city)
                city = donation.restaurant.city
                nearby_volunteers = VolunteerProfile.objects.filter(area__icontains=city, is_available=True)
                for volunteer in nearby_volunteers:
                    # Placeholder for notification logic (email, SMS, app notification)
                    print(f"Notify volunteer {volunteer.full_name} ({volunteer.phone}) for delivery of food request {donation.id} in {city}")
            except SurplusFoodRequest.DoesNotExist:
                pass
            return redirect("ngo_dashboard")

        elif action == "request_food":
            food_type = request.POST.get("food_type")
            quantity = request.POST.get("quantity")
            if food_type and quantity:
                NGOFoodRequest.objects.create(
                    ngo=profile,
                    food_type=food_type,
                    quantity=quantity,
                    fulfilled=False
                )
            return redirect("ngo_dashboard")

    # -------------------------------------------------
    # GEOCODING (STRUCTURED — NO OCEAN)
    # -------------------------------------------------
    lat = lng = None

    try:
        params = {
            "street": profile.address,
            "city": profile.city,
            "country": "India",
            "format": "json",
            "limit": 1,
        }

        res = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": "HappyTummy-App"},
            timeout=8,
        )

        data = res.json()
        print("GEOCODER RESPONSE:", data)

        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])

    except Exception as e:
        print("GEOCODING ERROR:", e)

    # -------------------------------------------------
    # FALLBACK (ONLY IF API FAILS)
    # -------------------------------------------------
    if not lat or not lng:
        lat, lng = 22.5726, 88.3639  # Kolkata

    # -------------------------------------------------
    # DASHBOARD DATA
    # -------------------------------------------------
    from datetime import timedelta
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # New/unpicked donations in the NGO's city (for this NGO to view/claim)
    new_donations = SurplusFoodRequest.objects.filter(
        restaurant__city__iexact=profile.city,
        is_picked=False,
        timestamp__gte=one_hour_ago
    ).select_related('restaurant')

    # Pending pickups: food accepted by NGO, waiting for volunteer delivery
    pending_pickups = PickupTask.objects.filter(
        request__restaurant__city__iexact=profile.city,
        completed=False,
        assigned_to__isnull=False,
        request__timestamp__gte=one_hour_ago
    ).select_related('request', 'assigned_to')

    # Completed pickups: food delivered by volunteer
    completed_pickups = PickupTask.objects.filter(
        request__restaurant__city__iexact=profile.city,
        completed=True,
        assigned_to__isnull=False,
        request__timestamp__gte=one_hour_ago
    ).select_related('request', 'assigned_to')

    # Recent food pickups (accepted donations in city, including in-progress)
    recent_food_pickups = PickupTask.objects.filter(
        request__restaurant__city__iexact=profile.city,
        request__isnull=False
    ).select_related('request', 'request__restaurant', 'assigned_to').order_by("-assigned_at")[:10]

    total_food_received = completed_pickups.count()
    pending_distributions = pending_pickups.count()
    completed_distributions = total_food_received

    # Monthly breakdown: % of food received by restaurant
    monthly_breakdown = PickupTask.objects.filter(
        completed=True,
        request__isnull=False,
        request__restaurant__city__iexact=profile.city,
        request__timestamp__gte=month_start
    ).values(
        "request__restaurant__business_name"
    ).annotate(
        total_qty=models.Sum("request__quantity")
    ).order_by("-total_qty")

    monthly_labels = [row["request__restaurant__business_name"] or "Unknown" for row in monthly_breakdown]
    monthly_values = [row["total_qty"] or 0 for row in monthly_breakdown]

    # -------------------------------------------------
    # RENDER
    # -------------------------------------------------
    return render(request, "dashboard/ngo_dashboard.html", {
        "profile": profile,
        "completed_pickups": completed_pickups,
        "new_donations": new_donations,
        "total_food_received": total_food_received,
        "pending_distributions": pending_distributions,
        "completed_distributions": completed_distributions,
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_values": json.dumps(monthly_values),
        "month_label": now.strftime("%B %Y"),
        "recent_food_pickups": recent_food_pickups,
        "lat": lat,
        "lng": lng,
        "my_food_requests": my_food_requests,
    })


@login_required(login_url="/")
@require_POST
def volunteer_location_update(request):
    try:
        profile = VolunteerProfile.objects.get(user=request.user)
    except VolunteerProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Volunteer profile not found."}, status=404)

    try:
        lat = float(request.POST.get("lat"))
        lng = float(request.POST.get("lng"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid latitude or longitude."}, status=400)

    if lat < -90 or lat > 90 or lng < -180 or lng > 180:
        return JsonResponse({"success": False, "error": "Coordinates out of range."}, status=400)

    profile.current_lat = lat
    profile.current_lng = lng
    profile.location_updated_at = timezone.now()
    profile.save(update_fields=["current_lat", "current_lng", "location_updated_at"])

    return JsonResponse({"success": True})


@login_required(login_url="/")
@require_GET
def ngo_live_volunteer_locations(request):
    try:
        ngo_profile = NGOProfile.objects.get(user=request.user)
    except NGOProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "NGO profile not found."}, status=404)

    # Volunteers currently assigned to in-progress tasks for this NGO.
    pending_tasks = PickupTask.objects.filter(
        request__isnull=False,
        request__restaurant__city__iexact=ngo_profile.city,
        completed=False,
        assigned_to__isnull=False,
    ).select_related("assigned_to", "request", "request__restaurant")

    volunteer_locations = []
    for task in pending_tasks:
        volunteer = task.assigned_to
        if not volunteer or volunteer.current_lat is None or volunteer.current_lng is None:
            continue

        volunteer_locations.append({
            "task_id": task.id,
            "volunteer_id": volunteer.id,
            "volunteer_name": volunteer.full_name,
            "phone": volunteer.phone,
            "lat": volunteer.current_lat,
            "lng": volunteer.current_lng,
            "updated_at": volunteer.location_updated_at.isoformat() if volunteer.location_updated_at else None,
            "food_type": task.request.food_type,
            "quantity": task.request.quantity,
            "pickup_from": task.request.restaurant.business_name,
        })

    return JsonResponse({"success": True, "locations": volunteer_locations})
