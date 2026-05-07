""" Null backend for tests — always denies course-level access. """


def permission_is_course_staff(user, course_id):
    return False
