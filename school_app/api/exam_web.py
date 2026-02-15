from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db

from models.exam_web_models import Grade, Exam, ExamTimetable , StudentMarks, OnlineExam,OnlineClass
from schemas.exam_web_schemas import GradeCreate, ExamCreate, ExamTimetableCreate, StudentMarksCreate, OnlineExamCreate, OnlineClassCreate
from schemas.admin_schemas import ResultResponse

from models.admin_models import SchoolStream,SchoolStreamClass,SchoolStreamSubject

from sqlalchemy import select, or_, tuple_, and_
from typing import List,Optional

from database.redis_cache import cache

exam_router = APIRouter(tags=["WEB API'S EXAM"])


@exam_router.post("/create_exam", response_model=ResultResponse, status_code=201)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db)
):
    exam = Exam(**payload.model_dump())

    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return ResultResponse(
        code = 200,
        status = "Success",
        message = "Exam created successfully",
        result = None
    )

   
@exam_router.post("/exam_timetable", response_model=ResultResponse, status_code=201)
async def create_exam_timetable(
    payload: ExamTimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    exam_timetable = ExamTimetable(**payload.model_dump())

    db.add(exam_timetable)
    await db.commit()
    await db.refresh(exam_timetable)

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam timetable created successfully",
    )


@exam_router.post("/marks", response_model=StudentMarksCreate)
def create_marks(payload: StudentMarksCreate, db: AsyncSession = Depends(get_db)):
    mark = StudentMarks(**payload.model_dump())
    db.add(mark)
    db.commit()
    db.refresh(mark)
    return mark


# grades
@exam_router.post("/grades", response_model=ResultResponse, status_code=201)
async def create_grade(
    payload: GradeCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Grade).where(
            Grade.start_range == payload.start_range,
            Grade.end_range == payload.end_range
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return ResultResponse(
            code=400,
            status="Failed",
            message="Grade range already exists",
            result=None
        )

    grade = Grade(
        start_range=payload.start_range,
        end_range=payload.end_range,
        grade=payload.grade
    )

    db.add(grade)
    await db.commit()
    await db.refresh(grade)

    return ResultResponse(
        code=201,
        status="Success",
        message="Grade created successfully",
        result={
            "grade_id": grade.grade_id,
            "start_range": grade.start_range,
            "end_range": grade.end_range,
            "grade": grade.grade,
            "is_active": grade.is_active
        }
    )

@exam_router.post("/grades/bulk", status_code=201)
async def create_grades_bulk(
    payload: List[GradeCreate],
    db: AsyncSession = Depends(get_db)
):
    seen_ranges = set()
    for item in payload:
        if item.start_range >= item.end_range:
            
            return ResultResponse(
                code=400,
                status="Failed",
                message=f"Invalid range {item.start_range}-{item.end_range}"
            )

        key = (item.start_range, item.end_range)
        if key in seen_ranges:
            return ResultResponse(
                code=400,
                status="Failed",
                message=f"Duplicate range in request: {key}"
            )
        seen_ranges.add(key)
        
    ranges = [(i.start_range, i.end_range) for i in payload]

    result = await db.execute(
        select(Grade.start_range, Grade.end_range)
        .where(
            tuple_(Grade.start_range, Grade.end_range).in_(ranges)
        )
    )
    existing = result.all()

    if existing:
        return ResultResponse(
                code=400,
                status="Failed",
                message=f"Duplicate range in request: {existing}",
                result=None
            )

    grades = [
        Grade(
            start_range=item.start_range,
            end_range=item.end_range,
            grade=item.grade
        )
        for item in payload
    ]

    db.add_all(grades)
    await db.commit()

    return ResultResponse(
        code=400,
        status="Failed",
        message="All grades created successfully",
        result=None
    )

 
 
# online_exam
@exam_router.post("/online_exam", response_model=ResultResponse)
async def create_online_exam(
    payload: OnlineExamCreate,
    db: AsyncSession = Depends(get_db)
):
    
    exam_check = await db.execute(select(OnlineExam).where(OnlineExam.exam_code == payload.exam_code))
    existing = exam_check.scalar_one_or_none()
    if existing:
        return ResultResponse(
            code=400,
            status="Failed",
            message = f"Online exam already exists for exam_code: {payload.exam_code} on date {payload.start_date}."
        )
    if payload.end_date < payload.start_date:
        return ResultResponse(
            code=400,
            status="Failed",
            message="End date must be greater than or equal to start date")
    try:    
        new_exam = OnlineExam( **payload.model_dump(exclude_unset=True))
        db.add(new_exam)
        await db.commit()
        await db.refresh(new_exam)

        return ResultResponse(
            code = 200,
            status = "Success",
            message = "Online exam created successfully",
            result =
                {
                    "id": new_exam.id,
                    "class_id": new_exam.class_id,
                    "subject_id": new_exam.subject_id,
                    "exam_code": new_exam.exam_code,
                    "url": new_exam.url,
                    "duration": new_exam.duration,
                    "start_date": new_exam.start_date,
                    "end_date": new_exam.end_date
                }
        )
    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message="Internal Server Error")


@exam_router.put("/online_exam", response_model=ResultResponse)
async def update_online_exam(
    exam_id: int,
    payload: OnlineExamCreate,   # all fields provided
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(OnlineExam).where(OnlineExam.id == exam_id)
        )
        exam = result.scalar_one_or_none()

        if not exam:
            return ResultResponse(
                code=400,
                status="Failed",
                message="Online exam not found"
            )

        # Date validation
        if payload.end_date < payload.start_date:
            return ResultResponse(
                code=400,
                status="Failed",
                message="End date must be greater than or equal to start date"
            )

        # ✅ NORMAL UPDATE (explicit assignment)
        exam.class_id = payload.class_id
        exam.subject_id = payload.subject_id
        exam.exam_code = payload.exam_code
        exam.url = payload.url
        exam.duration = payload.duration
        exam.start_date = payload.start_date
        exam.end_date = payload.end_date

        await db.commit()
        await db.refresh(exam)

        return ResultResponse(
            code=200,
            status="Success",
            message="Online exam updated successfully",
            result={
                "id": exam.id,
                "class_id": exam.class_id,
                "subject_id": exam.subject_id,
                "exam_code": exam.exam_code,
                "url": exam.url,
                "duration": exam.duration,
                "start_date": exam.start_date,
                "end_date": exam.end_date,
            }
        )

    except Exception:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message="Internal Server Error"
        )
    
    
@exam_router.get("/online_exam", response_model=ResultResponse)
async def get_online_exams(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    exam_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(OnlineExam)

        if class_id is not None:
            query = query.where(OnlineExam.class_id == class_id)

        if subject_id is not None:
            query = query.where(OnlineExam.subject_id == subject_id)

        if exam_code is not None:
            query = query.where(OnlineExam.exam_code == exam_code)

        result = await db.execute(query)
        exams = result.scalars().all()

        if not exams:
            return ResultResponse(
                code=400,
                status="Failed",
                message="No online exams found"
            )

        data = [{
                "id": exam.id,
                "class_id": exam.class_id,
                "subject_id": exam.subject_id,
                "exam_code": exam.exam_code,
                "url": exam.url,
                "duration": exam.duration,
                "start_date": exam.start_date,
                "end_date": exam.end_date,
                
            } for exam in exams]

        return ResultResponse(
            code=200,
            status="Success",
            message="Online exams fetched successfully",
            result={"data": data}
        )

    except Exception:
        return ResultResponse(
            code=500,
            status="Failed",
            message="Internal Server Error"
        )
    
    
# online_class
@exam_router.post("/online_class", response_model=ResultResponse)
async def create_online_class(
    payload: OnlineClassCreate,
    db: AsyncSession = Depends(get_db)
):
    
    if payload.end_date < payload.start_date:
        return ResultResponse(
            code=400,
            status="Failed",
            message="End date must be greater than or equal to start date")
    try:    
        new_exam = OnlineClass( **payload.model_dump(exclude_unset=True))
        db.add(new_exam)
        await db.commit()
        await db.refresh(new_exam)

        return ResultResponse(
            code=200,
            status="Success",
            message="Online exam created successfully",
            result={
                "id": new_exam.id,
                "class_id": new_exam.class_id,
                "subject_id": new_exam.subject_id,
                "url": new_exam.url,
                "duration": new_exam.duration,
                "start_date": new_exam.start_date,
                "end_date": new_exam.end_date,
            }
        )
    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message="Internal Server Error")

@exam_router.put("/online_class", response_model=ResultResponse)
async def update_online_exam(
    update_id: int,
    payload: OnlineExamCreate,
    db: AsyncSession = Depends(get_db)
):
    pass

@exam_router.get("/get_groupStreamClassList", response_model=ResultResponse)
async def groupStreamClassList(
    school_id:int,
    db: AsyncSession = Depends(get_db)
):    
    
    cache_key = f"school:{school_id}:stream:class:group:subject:meta"
    res_cached = await cache.get(cache_key)
    
    if res_cached:
        return ResultResponse(
        code=200,
        status="Success",
        message="Stream class fatched successfully(cache)",
        result=res_cached
    )
    stmt = (
        select(
            SchoolStream.school_stream_id,
            SchoolStream.stream_code,
            SchoolStreamClass.class_id,
            SchoolStreamClass.class_code,
            SchoolStreamSubject.subject_id,
            SchoolStreamSubject.subject_name
        )
        .join(
            SchoolStreamClass,
            SchoolStream.school_stream_id == SchoolStreamClass.school_stream_id
        )
        .outerjoin(
            SchoolStreamSubject,
            (SchoolStream.school_stream_id == SchoolStreamSubject.school_stream_id)
            & (SchoolStreamSubject.status == "active")  # filter here
        )
        .where(SchoolStreamClass.school_id == school_id)
        )
    
    
    result = await db.execute(stmt)
    rows = result.all()
    
    stream_list = {}
    class_sec = {}
    subject_list = {}
    for school_stream_id, stream_code, class_code, class_id, subject_name, subject_id in rows:
        stream_list[school_stream_id] = stream_code
        class_sec.setdefault(school_stream_id, {})[class_id] = class_code
        subject_list.setdefault(school_stream_id, {})[subject_name] = subject_id
    
    data = {
            "stream_list":stream_list,
            "class_sec":class_sec,
            "subject_list":subject_list
        }
    
    await cache.set(cache_key, value=data, expire=600)
    
    return ResultResponse(
        code=200,
        status="Success",
        message="Stream class fatched successfully",
        result=data
    )
    
 

 

# New
@exam_router.post("/New", response_model=ResultResponse, status_code=201)
async def create_grade(
    payload: GradeCreate,
    db: AsyncSession = Depends(get_db)
):
    pass