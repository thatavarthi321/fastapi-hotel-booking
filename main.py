from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="Grand Stay Hotel Room Booking API",
    description="FastAPI Final Project - Hotel Room Booking System",
    version="1.0.0"
)

# ==================================================
# DATA STORAGE
# ==================================================

rooms = [
    {"id": 1, "room_number": "101", "type": "Single", "price_per_night": 2000, "floor": 1, "is_available": True},
    {"id": 2, "room_number": "102", "type": "Double", "price_per_night": 3000, "floor": 1, "is_available": False},
    {"id": 3, "room_number": "201", "type": "Suite", "price_per_night": 5000, "floor": 2, "is_available": True},
    {"id": 4, "room_number": "202", "type": "Deluxe", "price_per_night": 4500, "floor": 2, "is_available": True},
    {"id": 5, "room_number": "301", "type": "Single", "price_per_night": 2200, "floor": 3, "is_available": False},
    {"id": 6, "room_number": "302", "type": "Double", "price_per_night": 3200, "floor": 3, "is_available": True},
]

bookings = []
booking_counter = 1


# ==================================================
# PYDANTIC MODELS
# ==================================================

class BookingRequest(BaseModel):
    guest_name: str = Field(..., min_length=2)
    room_id: int = Field(..., gt=0)
    nights: int = Field(..., gt=0, le=30)
    phone: str = Field(..., min_length=10)
    meal_plan: str = "none"
    early_checkout: bool = False


class NewRoom(BaseModel):
    room_number: str = Field(..., min_length=1)
    type: str = Field(..., min_length=2)
    price_per_night: int = Field(..., gt=0)
    floor: int = Field(..., gt=0)
    is_available: bool = True


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def find_room(room_id: int):
    for room in rooms:
        if room["id"] == room_id:
            return room
    return None


def find_booking(booking_id: int):
    for booking in bookings:
        if booking["booking_id"] == booking_id:
            return booking
    return None


def calculate_stay_cost(price_per_night, nights, meal_plan, early_checkout):
    room_cost = price_per_night * nights
    meal_cost = 0

    if meal_plan.lower() == "breakfast":
        meal_cost = 500 * nights
    elif meal_plan.lower() == "all-inclusive":
        meal_cost = 1200 * nights

    total = room_cost + meal_cost
    discount = 0

    if early_checkout:
        discount = total * 0.10
        total -= discount

    return total, discount


def filter_rooms_logic(room_type=None, max_price=None, floor=None, is_available=None):
    result = rooms

    if room_type is not None:
        result = [r for r in result if r["type"].lower() == room_type.lower()]

    if max_price is not None:
        result = [r for r in result if r["price_per_night"] <= max_price]

    if floor is not None:
        result = [r for r in result if r["floor"] == floor]

    if is_available is not None:
        result = [r for r in result if r["is_available"] == is_available]

    return result


# ==================================================
# HOME
# ==================================================

@app.get("/", tags=["Home"])
def home():
    return {"message": "Welcome to Grand Stay Hotel"}


# ==================================================
# ROOM ROUTES (FIXED ROUTES FIRST)
# ==================================================

# Summary
@app.get("/rooms/summary", tags=["Rooms"])
def room_summary():
    total_rooms = len(rooms)
    available_count = len([r for r in rooms if r["is_available"]])
    occupied_count = total_rooms - available_count
    prices = [r["price_per_night"] for r in rooms]

    room_types = {}
    for room in rooms:
        room_types[room["type"]] = room_types.get(room["type"], 0) + 1

    return {
        "total_rooms": total_rooms,
        "available_count": available_count,
        "occupied_count": occupied_count,
        "cheapest_room_price": min(prices),
        "most_expensive_room_price": max(prices),
        "rooms_by_type": room_types
    }


# Filter
@app.get("/rooms/filter", tags=["Rooms"])
def filter_rooms(
    room_type: str = Query(None),
    max_price: int = Query(None, gt=0),
    floor: int = Query(None, gt=0),
    is_available: bool = Query(None)
):
    result = filter_rooms_logic(room_type, max_price, floor, is_available)

    return {
        "filtered_rooms": result,
        "count": len(result)
    }


# Get all rooms
@app.get("/rooms", tags=["Rooms"])
def get_rooms():
    return {
        "rooms": rooms,
        "total": len(rooms),
        "available_count": len([r for r in rooms if r["is_available"]])
    }


# Add room
@app.post("/rooms", status_code=201, tags=["Rooms"])
def create_room(data: NewRoom):
    for room in rooms:
        if room["room_number"] == data.room_number:
            raise HTTPException(status_code=400, detail="Room number already exists")

    new_id = max(room["id"] for room in rooms) + 1

    new_room = {
        "id": new_id,
        "room_number": data.room_number,
        "type": data.type,
        "price_per_night": data.price_per_night,
        "floor": data.floor,
        "is_available": data.is_available
    }

    rooms.append(new_room)
    return new_room


# Search rooms
@app.get("/rooms/search", tags=["Rooms"])
def search_rooms(keyword: str):
    result = [
        room for room in rooms
        if keyword.lower() in room["room_number"].lower()
        or keyword.lower() in room["type"].lower()
    ]

    if not result:
        return {
            "message": "No matching rooms found",
            "total_found": 0
        }

    return {
        "matches": result,
        "total_found": len(result)
    }


# Sort rooms
@app.get("/rooms/sort", tags=["Rooms"])
def sort_rooms(
    sort_by: str = "price_per_night",
    order: str = "asc"
):
    allowed = ["price_per_night", "floor", "type"]

    if sort_by not in allowed:
        raise HTTPException(status_code=400, detail="Invalid sort_by field")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order value")

    reverse_order = order == "desc"

    sorted_rooms = sorted(rooms, key=lambda x: x[sort_by], reverse=reverse_order)

    return {
        "sorted_by": sort_by,
        "order": order,
        "rooms": sorted_rooms
    }


# Pagination
@app.get("/rooms/page", tags=["Rooms"])
def paginate_rooms(
    page: int = Query(1, gt=0),
    limit: int = Query(2, gt=0)
):
    total = len(rooms)
    total_pages = (total + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "rooms": rooms[start:end]
    }


# Combined browse
@app.get("/rooms/browse", tags=["Rooms"])
def browse_rooms(
    keyword: str = None,
    sort_by: str = "price_per_night",
    order: str = "asc",
    page: int = Query(1, gt=0),
    limit: int = Query(3, gt=0)
):
    result = rooms.copy()

    if keyword is not None:
        result = [
            room for room in result
            if keyword.lower() in room["room_number"].lower()
            or keyword.lower() in room["type"].lower()
        ]

    allowed = ["price_per_night", "floor", "type"]

    if sort_by not in allowed:
        raise HTTPException(status_code=400, detail="Invalid sort_by")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    reverse_order = order == "desc"
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse_order)

    total = len(result)
    total_pages = (total + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit

    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_results": total,
        "total_pages": total_pages,
        "rooms": result[start:end]
    }


# Get room by ID
@app.get("/rooms/{room_id}", tags=["Rooms"])
def get_room(room_id: int):
    room = find_room(room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return room


# Update room
@app.put("/rooms/{room_id}", tags=["Rooms"])
def update_room(
    room_id: int,
    price_per_night: int = Query(None, gt=0),
    is_available: bool = Query(None)
):
    room = find_room(room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if price_per_night is not None:
        room["price_per_night"] = price_per_night

    if is_available is not None:
        room["is_available"] = is_available

    return room


# Delete room
@app.delete("/rooms/{room_id}", tags=["Rooms"])
def delete_room(room_id: int):
    room = find_room(room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room["is_available"]:
        raise HTTPException(status_code=400, detail="Occupied room cannot be deleted")

    rooms.remove(room)
    return {"message": "Room deleted successfully"}


# ==================================================
# BOOKING ROUTES
# ==================================================

# Get bookings
@app.get("/bookings", tags=["Bookings"])
def get_bookings():
    return {
        "bookings": bookings,
        "total": len(bookings)
    }


# Active bookings
@app.get("/bookings/active", tags=["Bookings"])
def active_bookings():
    active = [
        booking for booking in bookings
        if booking["status"] in ["confirmed", "checked_in"]
    ]

    return {
        "active_bookings": active,
        "total": len(active)
    }


# Search bookings
@app.get("/bookings/search", tags=["Bookings"])
def search_bookings(guest_name: str):
    result = [
        booking for booking in bookings
        if guest_name.lower() in booking["guest_name"].lower()
    ]

    return {
        "matches": result,
        "total_found": len(result)
    }


# Sort bookings
@app.get("/bookings/sort", tags=["Bookings"])
def sort_bookings(sort_by: str = "total_cost"):
    allowed = ["total_cost", "nights"]

    if sort_by not in allowed:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    sorted_data = sorted(bookings, key=lambda x: x[sort_by])

    return {
        "sorted_by": sort_by,
        "bookings": sorted_data
    }


# Create booking
@app.post("/bookings", tags=["Bookings"])
def create_booking(data: BookingRequest):
    global booking_counter

    room = find_room(data.room_id)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not room["is_available"]:
        raise HTTPException(status_code=400, detail="Room is already occupied")

    total_cost, discount = calculate_stay_cost(
        room["price_per_night"],
        data.nights,
        data.meal_plan,
        data.early_checkout
    )

    room["is_available"] = False

    booking = {
        "booking_id": booking_counter,
        "guest_name": data.guest_name,
        "phone": data.phone,
        "room_id": room["id"],
        "room_number": room["room_number"],
        "room_type": room["type"],
        "nights": data.nights,
        "meal_plan": data.meal_plan,
        "early_checkout": data.early_checkout,
        "discount": discount,
        "total_cost": total_cost,
        "status": "confirmed"
    }

    bookings.append(booking)
    booking_counter += 1

    return booking


# Check-in
@app.post("/checkin/{booking_id}", tags=["Workflow"])
def checkin_booking(booking_id: int):
    booking = find_booking(booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["status"] == "checked_out":
        raise HTTPException(status_code=400, detail="Cannot check-in after checkout")

    booking["status"] = "checked_in"
    return booking


# Checkout
@app.post("/checkout/{booking_id}", tags=["Workflow"])
def checkout_booking(booking_id: int):
    booking = find_booking(booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["status"] == "checked_out":
        raise HTTPException(status_code=400, detail="Already checked out")

    booking["status"] = "checked_out"

    room = find_room(booking["room_id"])
    if room:
        room["is_available"] = True

    return booking
