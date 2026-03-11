from api.admin_web import admin_router
from api.student_web import student_router
from api.teacher_web import teacher_router
from api.transport import transport_router
from api.exam_web import exam_router
from api.common import common_router
from api.time_table import time_table_router, time_table_client_router
from api.dashboard_client import dashboard_routers
from api.gallery_web import gallery_web_router, gallery_client_router
from api.event_web import event_web_router, event_client_router
from api.banner_web import banner_web_router, banner_client_router
from api.online_class_web import online_class_web_router, online_class_client_router
from api.notice_web import notice_web_router, notice_client_router


ROUTERS = [
    (admin_router,               "/api/web/admin"),
    (student_router,             "/api/web/student"),
    (teacher_router,             "/api/web/teacher"),
    (exam_router,                "/api/web/exam"),
    (time_table_router,          "/api/web/exam"),          # WEB   → /api/web/exam/time_table
    (transport_router,           "/api/web/transport"),
    (common_router,              "/api/web/common"),
    (gallery_web_router,         "/api/web/admin"),         # WEB   → /api/web/admin/gallery
    (event_web_router,           "/api/web/admin"),         # WEB   → /api/web/admin/event
    (banner_web_router,          "/api/web/admin"),         # WEB   → /api/web/admin/banner
    (online_class_web_router,    "/api/web/admin"),         # WEB   → /api/web/admin/online-class
    (notice_web_router,          "/api/web/admin"),         # WEB   → /api/web/admin/notice
    (dashboard_routers,          "/api/client/dashboard"),
    (gallery_client_router,      "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/gallery
    (event_client_router,        "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/event
    (banner_client_router,       "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/banner
    (online_class_client_router, "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/online-class
    (notice_client_router,       "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/notice
    (time_table_client_router,   "/api/client/dashboard"),  # CLIENT → /api/client/dashboard/timetable
]
