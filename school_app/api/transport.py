from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.transport_models import VehicleDetails, Route, VehicleRouteMap, TransportationStudent,VehicleExpense

from schemas.transport_schemas import VehicleDetailsCreate, RouteCreate, TransportationStudentCreate,VehicleExpenseCreate,\
    VehicleRouteMapCreate

from schemas.admin_schemas import ResultResponse
from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional

from database.redis_cache import cache

transport_router = APIRouter(tags=["WEB API'S TRANSPORTS"])


@transport_router.post("/vehicle", response_model=ResultResponse)
async def vehicle(
    payload: Optional[VehicleDetailsCreate] = None,
    action: str = Query(...),
    update_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        # 🔹 UPDATE VEHICLE
        if action.lower() == "update_vehicle":
            if not update_id:
                raise HTTPException(
                    status_code=400,
                    detail="update_id is required when action=update_vehicle"
                )

            stmt = select(VehicleDetails).where(VehicleDetails.id == update_id)
            result = await db.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if not vehicle:
                return ResultResponse(
                    code=404,
                    status="Failed",
                    message="Vehicle not found"
                )

            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(vehicle, key, value)

            await db.commit()
            await db.refresh(vehicle)

            return ResultResponse(
                code=200,
                status="Success",
                message="Vehicle updated successfully",
                result={
                    "vehicle_id": vehicle.id,
                    "vehicle_no": vehicle.vehicle_no
                }
            )

        # 🔹 CREATE VEHICLE
        elif action.lower() == "create_vehicle":
            stmt = select(VehicleDetails).where(VehicleDetails.vehicle_no == payload.vehicle_no)
            result = await db.execute(stmt)
            existing_vehicle = result.scalars().first()
            if existing_vehicle:
                return ResultResponse(
                code=409,
                status="Failed",
                message="School user already exist",
                result = {
                    "existing_vehicle":existing_vehicle.vehicle_no,
                    "status":existing_vehicle.status})
                
            new_vehicle = VehicleDetails(
                **payload.model_dump(exclude_unset=True)
            )
            db.add(new_vehicle)
            await db.commit()
            await db.refresh(new_vehicle)

            return ResultResponse(
                code=201,
                status="Success",
                message="Vehicle created successfully",
                result={
                    "vehicle_id": new_vehicle.id,
                    "status":new_vehicle.status
                }
            )

        # 🔹 DELETE VEHICLE
        elif action.lower() == "delete_vehicle":
            if not update_id:
                raise HTTPException(
                    status_code=400,
                    detail="update_id is required when action=delete_vehicle"
                )

            stmt = select(VehicleDetails).where(VehicleDetails.id == update_id)
            result = await db.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if not vehicle:
                return ResultResponse(
                    code=404,
                    status="Failed",
                    message="Vehicle not found"
                )

            await db.delete(vehicle)
            await db.commit()

            return ResultResponse(
                code=200,
                status="Success",
                message="Vehicle deleted successfully",
                result={
                    "vehicle_id": vehicle.id
                }
            )

        else:
            return ResultResponse(
                code=400,
                status="Failed",
                message="Invalid action"
            )

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database constraint violation {str(e)}"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@transport_router.get("/vehicle", response_model=ResultResponse)
async def get_all_vehicles(
    action: Optional[int] = Query(None, description="Vehicle ID"),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(VehicleDetails)
        if action == "vehicle_no":
            stmt = stmt.where(VehicleDetails.vehicle_no == action)

        elif action == "driver_name":
            stmt = stmt.where(VehicleDetails.driver_name == action)

        elif action == "helper_name":
            stmt = stmt.where(VehicleDetails.helper_name == action)

        result = await db.execute(stmt)
        vehicles = result.scalars().all()

        if not vehicles:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No vehicles found",
                result=[]
            )

        data = [
            {
                "id": item.id,
                "vehicle_no": item.vehicle_no,
                "vehicle_capacity": item.vehicle_capacity,
                "vehicle_reg_no": item.vehicle_reg_no,
                "status": item.status,
                "driver_name": item.driver_name,
                "helper_name": item.helper_name
            }
            for item in vehicles
        ]

        return ResultResponse(
            code=200,
            status="Success",
            message="Vehicles fetched successfully",
            result={"vehicles_list": data}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
        
@transport_router.post("/route", response_model=ResultResponse)
async def create_route(
    payload: RouteCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        route = Route(**payload.model_dump(exclude_unset=True))
        db.add(route)
        await db.commit()
        await db.refresh(route)

        return ResultResponse(
            code=201,
            status="Success",
            message="Route created successfully",
            result={"route_id": route.id}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@transport_router.post("/vehicle-route-map", response_model=ResultResponse)
async def map_vehicle_to_route(
    payload: VehicleRouteMapCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        mapping = VehicleRouteMap(**payload.model_dump(exclude_unset=True))
        db.add(mapping)
        await db.commit()
        await db.refresh(mapping)

        return ResultResponse(
            code=201,
            status="Success",
            message="Vehicle mapped to route successfully",
            result={"id": mapping.id}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@transport_router.post("/transportation-student", response_model=ResultResponse)
async def create_transport_student(
    payload: TransportationStudentCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        transport = TransportationStudent(
            **payload.model_dump(exclude_unset=True)
        )
        db.add(transport)
        await db.commit()
        await db.refresh(transport)

        return ResultResponse(
            code=201,
            status="Success",
            message="Transportation student added",
            result={"id": transport.id}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@transport_router.post("/vehicle-expense", response_model=ResultResponse)
async def create_vehicle_expense(
    payload: VehicleExpenseCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        expense = VehicleExpense(**payload.model_dump(exclude_unset=True))
        db.add(expense)
        await db.commit()
        await db.refresh(expense)

        return ResultResponse(
            code=201,
            status="Success",
            message="Vehicle expense added",
            result={"expense_id": expense.id}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

