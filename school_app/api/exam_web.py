from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db

from models.exam_web_models import Grade, Exam, ExamTimetable , StudentMarks, OnlineExam,OnlineClass
from schemas.exam_web_schemas import GradeCreate, ExamCreate, ExamTimetableCreate, ExamTimetableUpdate,StudentMarksCreate, OnlineExamCreate, OnlineClassCreate, ExamUpdate
from schemas.admin_schemas import ResultResponse

from models.admin_models import SchoolStream,SchoolStreamClass,SchoolStreamSubject

from sqlalchemy import select, or_, tuple_, and_
from typing import List,Optional
from fastapi import Query
from database.redis_cache import cache

exam_router = APIRouter(tags=["WEB API'S EXAM"])
    
# grades
@exam_router.post("/grades", response_model=ResultResponse)
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

@exam_router.post("/grades/bulk",response_model=ResultResponse)
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

@exam_router.delete(
    "/grades/{grade_id}",
    response_model=ResultResponse,
    summary="Delete Grade",
    description="Permanently delete a grade entry"
)
async def delete_grade(
    grade_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Grade).where(Grade.grade_id == grade_id)
    )
    grade = result.scalar_one_or_none()

    if not grade:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Grade not found",
            result=None
        )

    await db.delete(grade)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Grade deleted successfully",
        result=None
    )
    
@exam_router.post("/create_exam", response_model=ResultResponse)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if exam_name already exists
    result = await db.execute(
        select(Exam).where(Exam.exam_name == payload.exam_name)
    )
    existing_exam = result.scalar_one_or_none()

    if existing_exam:
        return ResultResponse(
            code=400,
            status="Failed",
            message="Exam with this name already exists",
            result=None
        )

    exam = Exam(**payload.model_dump())

    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam created successfully",
        result=None
    )

@exam_router.get("/get_exams_list", response_model=ResultResponse)
async def get_exams_by_class(
    school_stream_id: Optional[int] = Query(None),
    is_active: Optional[int] = Query(None, ge=0, le=1),
    db: AsyncSession = Depends(get_db)
):
    query = select(Exam)

    # Dynamic filters
    if school_stream_id is not None:
        query = query.where(Exam.school_stream_id == school_stream_id)

    if is_active is not None:
        query = query.where(Exam.is_active == is_active)

    result = await db.execute(query)
    exams = result.scalars().all()

    data = [
        {
            "exam_id": item.exam_id,
            "exam_name": item.exam_name,
            "school_stream_id": item.school_stream_id,
            "session_yr": item.session_yr,
            "exam_description": item.exam_description,
            "is_active": item.is_active
        }
        for item in exams
    ]

    return ResultResponse(
        code=200,
        status="Success",
        message="Exams fetched successfully",
        result={"data": data}
    )
 
@exam_router.put("/exam/{exam_id}",response_model=ResultResponse,summary="Update Exam",description="Update an existing exam using exam ID")
async def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if exam exists
        result = await db.execute(
            select(Exam).where(Exam.exam_id == exam_id)
        )
        exam = result.scalar_one_or_none()

        if not exam:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Exam not found",
                result={}
            )

        # Get only provided fields
        update_data = exam_data.model_dump(exclude_unset=True)

        # Prevent empty update
        if not update_data:
            return ResultResponse(
                code=400,
                status="Failed",
                message="No fields provided for update",
                result={}
            )

        # Validate foreign key if updating school_stream_id
        if "school_stream_id" in update_data:
            stream_result = await db.execute(
                select(SchoolStream).where(
                    SchoolStream.school_stream_id == update_data["school_stream_id"]
                )
            )
            stream = stream_result.scalar_one_or_none()

            if not stream:
                return ResultResponse(
                    code=400,
                    status="Failed",
                    message="Invalid school_stream_id",
                    result={}
                )

        # Update fields dynamically
        for field, value in update_data.items():
            setattr(exam, field, value)

        await db.commit()
        await db.refresh(exam)

        return ResultResponse(
            code=200,
            status="Success",
            message="Exam updated successfully",
            result={
                "exam_id": exam.exam_id,
                "exam_name": exam.exam_name,
                "school_stream_id": exam.school_stream_id,
                "session_yr": exam.session_yr,
                "exam_description": exam.exam_description,
                "is_active": exam.is_active
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=str(e),
            result={}
        )
    
@exam_router.delete("/exam/{exam_id}", response_model=ResultResponse,summary="Delete Exam",description="Delete an existing exam using exam ID")
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Check if exam exists
    result = await db.execute(
        select(Exam).where(Exam.exam_id == exam_id)
    )
    exam = result.scalar_one_or_none()

    if not exam:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Exam not found",
            result={}
        )

    # Delete exam
    await db.delete(exam)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam deleted successfully",
        result={}
    )
    

@exam_router.post("/exam_timetable",response_model=ResultResponse,summary="Create Exam Timetable",
    description="Create a new exam timetable entry"
)
async def create_exam_timetable(
    payload: ExamTimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    
    # Check if exam timetable already exists for this exam
    result = await db.execute(
        select(ExamTimetable.exam_id).where(ExamTimetable.exam_id == payload.exam_id)
    )
    existing_exam = result.scalar_one_or_none()

    if existing_exam:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Exam timetable already created for this exam",
            result={}
        )

    exam_timetable = ExamTimetable(**payload.model_dump())

    db.add(exam_timetable)
    await db.commit()
    await db.refresh(exam_timetable)

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam timetable created successfully",
        result={"id": exam_timetable.timetable_id}
    )


@exam_router.put(
    "/exam_timetable/{timetable_id}",
    response_model=ResultResponse,
    summary="Update Exam Timetable",
    description="Update an existing exam timetable entry"
)
async def update_exam_timetable(
    timetable_id: int,
    payload: ExamTimetableUpdate,
    db: AsyncSession = Depends(get_db)
):

    # Check if timetable exists
    result = await db.execute(
        select(ExamTimetable).where(
            ExamTimetable.timetable_id == timetable_id
        )
    )
    exam_timetable = result.scalar_one_or_none()

    if not exam_timetable:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Exam timetable not found",
            result={}
        )

    # Prevent duplicate exam_id (if changed)
    if payload.exam_id:
        result = await db.execute(
            select(ExamTimetable).where(
                ExamTimetable.exam_id == payload.exam_id,
                ExamTimetable.timetable_id != timetable_id
            )
        )
        existing_exam = result.scalar_one_or_none()

        if existing_exam:
            return ResultResponse(
                code=400,
                status="Failed",
                message="Another timetable already exists for this exam",
                result={}
            )

    # Update only provided fields
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(exam_timetable, key, value)

    await db.commit()
    await db.refresh(exam_timetable)

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam timetable updated successfully",
        result={"id": exam_timetable.timetable_id}
    )
    
@exam_router.get("/exam_timetable",response_model=ResultResponse,summary="Get Exam Timetable",
    description="Filter by stream_id, exam_id and exam_name"
)
async def get_exam_timetable(
    school_stream_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    exam_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(ExamTimetable).join(Exam)

    if school_stream_id:
        query = query.where(ExamTimetable.school_stream_id == school_stream_id)

    if exam_id:
        query = query.where(ExamTimetable.exam_id == exam_id)

    if exam_name:
        query = query.where(Exam.exam_name.ilike(f"%{exam_name}%"))

    result = await db.execute(query)
    timetables = result.scalars().all()

    data = []
    for item in timetables:
        data.append({
            "id": item.timetable_id,
            "exam_id": item.exam_id,
            "school_stream_id": item.school_stream_id,
            "school_group_id": item.school_group_id,
            "subject_id": item.subject_id,
            "total_marks": item.total_marks,
            "pass_mark": item.pass_mark,
            "exam_start_date": item.exam_start_date,
            "exam_end_date": item.exam_end_date,
            "start_time": item.start_time,
            "end_time": item.end_time,
            "is_active": item.is_active
        })

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam timetable fetched successfully",
        result={"data":data}
    )
   
    
@exam_router.delete(
    "/exam_timetable/{timetable_id}",
    response_model=ResultResponse,
    summary="Delete Exam Timetable",
    description="Permanently delete an exam timetable entry"
)
async def delete_exam_timetable(
    timetable_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Check if timetable exists
    result = await db.execute(
        select(ExamTimetable).where(
            ExamTimetable.timetable_id == timetable_id
        )
    )
    exam_timetable = result.scalar_one_or_none()

    if not exam_timetable:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Exam timetable not found",
            result={}
        )

    await db.delete(exam_timetable)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Exam timetable deleted successfully",
        result={}
    )
    
    
@exam_router.post("/marks_entry", response_model=ResultResponse)
async def create_marks(
    payload: StudentMarksCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        subject_ids = [sub.subject_id for sub in payload.subjects]

        # Check existing marks for this student for given subjects
        result = await db.execute(
            select(StudentMarks.subject_id).where(
                StudentMarks.student_id == payload.student_id,
                StudentMarks.subject_id.in_(subject_ids)
            )
        )

        existing_subjects = set(result.scalars().all())

        if existing_subjects:
            return ResultResponse(
                code=400,
                status="Failed",
                message=f"Marks already exist for subjects: {list(existing_subjects)}",
                result={}
            )

        # Prepare bulk insert
        marks_objects = []

        for sub in payload.subjects:
            marks_objects.append(
                StudentMarks(
                    student_id=payload.student_id,
                    class_id=payload.class_id,
                    subject_id=sub.subject_id,
                    mark=sub.mark
                )
            )

        db.add_all(marks_objects)

        await db.commit()

        return ResultResponse(
            code=200,
            status="Success",
            message="Marks created successfully",
            result={"subjects_inserted": len(marks_objects)}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=str(e),
            result={}
        )
 
# online_exam
@exam_router.post("/create_online_exam", response_model=ResultResponse)
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
    
   
@exam_router.get("/get_online_exam", response_model=ResultResponse)
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
@exam_router.post("/create_online_class", response_model=ResultResponse)
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
