from api.admin_web import admin_router

from api.student_web import student_router
from api.teacher_web import teacher_router

from api.transport import transport_router

from api.exam_web import exam_router

from api.common import common_router
from api.time_table import time_table_router


ROUTERS = [
    (admin_router, "/api/web/admin"),
    (student_router, "/api/web/student"),
    (teacher_router, "/api/web/teacher"),
    (exam_router, "/api/web/exam"),
    (time_table_router, "/api/web/exam"),
    (transport_router, "/api/web/transport"),
    (common_router, "/api/web/common"),
]


