# encoding=utf-8
import os
import hashlib
import copy

import web
import xconfig
import xtables
import xutils

from xutils import ConfigParser
from web.utils import Storage

config = xconfig
# 用户配置
_users = None


def _get_users():
    """获取用户，内部接口"""
    global _users

    # 有并发风险
    if _users is not None:
        return _users

    # defaults = read_users_from_ini("config/users.default.ini")
    # customs  = read_users_from_ini("config/users.ini")
    db = xtables.get_user_table()
    db_users = db.select()
    db_users = list(db_users)

    _users = {}
    # 默认的账号
    _users["admin"] = Storage(name="admin", password="123456")

    # print(db_users)

    for user in db_users:
        _users[user.name] = user
    
    return _users

def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    return copy.deepcopy(_get_users())


def refresh_users():
    global _users
    _users = None
    print("refresh users")
    return _get_users()

def get_user(name):
    users = _get_users()
    if xconfig.IS_TEST:
        return users.get("admin")
    return users.get(name)

def get_user_password(name):
    users = _get_users()
    return users[name]["password"]

def get_current_user():
    if xconfig.IS_TEST:
        return get_user("admin")
    return get_user(web.cookies().get("xuser"))

def get_current_role():
    """获取当前用户的角色"""
    user = get_current_user()
    return user.get("name")

def get_md5_hex(pswd):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()

def get_password_md5(passwd):
    passwd = passwd + xutils.format_date()
    pswd_md5 = hashlib.md5()
    pswd_md5.update(passwd.encode("utf-8"))
    return pswd_md5.hexdigest()

def add_user(name, password):
    users = _get_users()
    user = Storage(name=name, password=password)
    users[name] = user
    db = xtables.get_user_table()
    exist = db.select_one(where=dict(name=name))
    if exist is None:
        db.insert(name=name,password=password,ctime=xutils.format_time())
    else:
        db.update(where=dict(name=name), password=password)

def has_login(name=None):
    # import threading
    """验证是否登陆

    如果``name``指定,则只能该用户名通过验证
    """
    if config.IS_TEST:
        return True
    name_in_cookie = web.cookies().get("xuser")
    pswd_in_cookie = web.cookies().get("xpass")

    # TODO 不同地方调用结果不一致
    # print(name, name_in_cookie)
    if name is not None and name_in_cookie != name:
        return False
    name = name_in_cookie
    if name == "" or name is None:
        return False
    user = get_user(name)
    # print(threading.current_thread().name, " -- User --", user)
    if user is None:
        return False

    password_md5 = get_password_md5(user["password"])
    return password_md5 == pswd_in_cookie

def is_admin():
    return config.IS_ADMIN or has_login("admin")

def check_login(user_name=None):
    if not has_login(user_name):
        raise web.seeother("/unauthorized")

def login_required(user_name=None):
    """管理员验证装饰器"""
    def _login_required(func):
        def new_func(*args, **kw):
            check_login(user_name)
            ret = func(*args, **kw)
            return ret
        return new_func
    return _login_required

