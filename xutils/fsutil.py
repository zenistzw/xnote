# encoding=utf-8
# @modified 2019/04/07 23:15:03
import codecs
import os
import platform
import xutils
import base64
import time
import xconfig
from .imports import *
from . import logutil
from web.utils import Storage

def get_real_path(path):
    if path == None:
        return None
    if xconfig.USE_URLENCODE:
        return quote_unicode(path)
    return path

def makedirs(dirname):
    '''检查并创建目录(如果不存在不报错)'''
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def readfile(path, mode = "r", limit = -1):
    '''读取文件，尝试多种编码，编码别名参考标准库`Lib/encodings/aliases.py`
    * utf-8 是一种边长编码，兼容ASCII
    * gbk 是一种双字节编码，全称《汉字内码扩展规范》，兼容GB2312
    * latin_1 是iso-8859-1的别名，单字节编码，兼容ASCII
    '''
    last_err = None
    for encoding in ("utf-8", "gbk", "mbcs", "latin_1"):
        try:
            if PY2:
                with open(path) as fp:
                    if limit > 0:
                        content = fp.read(limit)
                    else:
                        content = fp.read()
                    return content.decode(encoding)
            else:
                with open(path, encoding=encoding) as fp:
                    if limit > 0:
                        content = fp.read(limit)
                    else:
                        content = fp.read()
                    return content
        except Exception as e:
            last_err = e
    raise Exception("can not read file %s" % path, last_err)

def readlines(fpath, limit = -1):
    with open(fpath, encoding="utf-8") as fp:
        if limit <= 0:
            return fp.readlines()
        else:
            lines = []
            for n in range(limit):
                lines.append(fp.readline())
            return lines

# readfile别名
read      = readfile
read_utf8 = readfile

def writefile(path, content):
    import codecs
    dirname = os.path.dirname(path)
    makedirs(dirname)

    with open(path, mode="wb") as fp:
        if is_str(content):
            buf = codecs.encode(content, "utf-8")
        else:
            buf = content
        fp.write(buf)
    return content

savetofile = writefile
savefile   = writefile
writebytes = writefile

def readbytes(path):
    with open(path, "rb") as fp:
        bytes = fp.read()
    return bytes

def rmfile(path, hard = False):
    """删除文件，默认软删除，移动到trash目录中，如果已经在trash目录或者硬删除，从磁盘中抹除
    @param {str} path
    @param {bool} hard=False 是否硬删除
    @return {str} path in trash.
    """
    if not os.path.exists(path):
        # 尝试转换一下path
        path = get_real_path(path)
        if not os.path.exists(path):
            return
    if os.path.isfile(path):
        if hard:
            os.remove(path)
            return
        dirname = os.path.dirname(path)
        dirname = os.path.abspath(dirname)
        dustbin = os.path.abspath(xconfig.TRASH_DIR)
        if dirname == dustbin:
            os.remove(path)
        else:
            fname = os.path.basename(path)
            name, ext = os.path.splitext(fname)
            suffix = 0
            while True:
                suffix += 1
                destpath = os.path.join(dustbin, "%s@%s@%s%s" % (name, time.strftime("%Y%m%d"), suffix, ext))
                if not os.path.exists(destpath):
                    break
            # os.rename(path, destpath)
            # shutil.move 可以跨磁盘分区移动文件
            shutil.move(path, destpath)
        # os.remove(path)
    elif os.path.isdir(path):
        if hard:
            shutil.rmtree(path)
            return
        path = path.rstrip("/")
        basename = os.path.basename(path)
        target = os.path.join(xconfig.TRASH_DIR, basename)
        target = os.path.abspath(target)
        path   = os.path.abspath(path)
        if target == path:
            # 已经在回收站，直接删除文件夹
            shutil.rmtree(path)
            return
        else:
            suffix = 0
            while True:
                suffix += 1
                if os.path.exists(target):
                    tmp_name = "%s@%s" % (basename, suffix)
                    target = os.path.join(xconfig.TRASH_DIR, tmp_name)
                else:
                    shutil.move(path, target)
                    break
            return target

remove = rmfile
remove_file = rmfile

def copy(src, dest):
    bufsize = 64 * 1024 # 64k
    srcfp = open(src, "rb")
    destfp = open(dest, "wb")

    try:
        while True:
            buf = srcfp.read(bufsize)
            if not buf:
                break
            destfp.write(buf)
    except Exception as e:
        logutil.error("copy file from {} to {} failed", src, dest, e)

    srcfp.close()
    destfp.close()

def get_file_ext(fname):
    if '.' not in fname:return ''
    return fname.split('.')[-1]

def format_size(size):
    """格式化大小
        >>> format_size(10240)
        '10.00K'
    """
    if size < 1024:
        return '%sB' % size
    elif size < 1024 **2:
        return '%.2fK' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2fM' % (float(size) / 1024 ** 2)
    elif size < 1024 ** 4:
        return '%.2fG' % (float(size) / 1024 ** 3)
    else:
        return '%.2fT' % (float(size) / 1024 ** 4)


def format_file_size(fpath):
    """获取文件大小"""
    return get_file_size(fpath, format=True)

def rename_file(srcname, dstname):
    dest_dirname = os.path.dirname(dstname)
    if not os.path.exists(dest_dirname):
        os.makedirs(dest_dirname)
    os.rename(srcname, dstname)


def open_directory(dirname):
    if os.name == "nt":
        os.popen("explorer %s" % dirname)
    elif platform.system() == "Darwin":
        os.popen("open %s" % dirname)

def get_file_size(filepath, format=False):
    try:
        st = os.stat(filepath)
        if st and st.st_size >= 0:
            if format:
                return format_size(st.st_size)
            else:
                return st.st_size
    except OSError as e:
        pass
    if format:
        return "-"
    else:
        return -1


def get_relative_path(path, parent):
    """获取文件相对parent的路径
        >>> get_relative_path('/users/xxx/test/hello.html', '/users/xxx')
        'test/hello.html'
    """
    path1 = os.path.abspath(path)
    parent1 = os.path.abspath(parent)
    # abpath之后最后没有/
    # 比如
    # ./                 -> /users/xxx
    # ./test/hello.html  -> /users/xxx/test/hello.html
    # 相减的结果是       -> /test/hello.html
    # 需要除去第一个/
    relative_path = path1[len(parent1):]
    return relative_path.replace("\\", "/")[1:]

class FileItem(Storage):

    def __init__(self, path, parent=None):
        self.path = path
        self.name = os.path.basename(path)
        self.size = '-'
        self.cdate = '-'
        _, self.ext = os.path.splitext(path)
        self.ext = self.ext.lower()

        if parent != None:
            self.name = get_relative_path(path, parent)

        # 处理Windows盘符
        if path.endswith(":"):
            self.name = path

        self.name = xutils.unquote(self.name)
        if os.path.isfile(path):
            self.type = "file"
            self.name = decode_name(self.name)
            _, self.ext = os.path.splitext(self.name)
        else:
            self.type = "dir"
            self.path += "/"

        try:
            st = os.stat(path)
            self.size = format_size(st.st_size)
            self.cdate = xutils.format_date(st.st_ctime)
        except:
            pass

    # sort方法重写__lt__即可
    def __lt__(self, other):
        if self.type == "dir" and other.type == "file":
            return True
        if self.type == "file" and other.type == "dir":
            return False
        return self.name < other.name

    # 兼容Python2
    def __cmp__(self, other):
        if self.type == other.type:
            return cmp(self.name, other.name)
        if self.type == "dir":
            return -1
        return 1

def list_files(dirname):
    filelist = [FileItem(os.path.join(dirname, child)) for child in os.listdir(dirname)]
    filelist.sort()
    return filelist

def splitpath(path):
    """拆分文件路径
    :arg str path:
    """
    path   = os.path.abspath(path)
    path   = path.replace("\\", "/")
    pathes = path.split("/")
    if path[0] == "/":
        last = ""
    else:
        last = None
    pathlist = []
    for vpath in pathes:
        if vpath == "":
            continue
        if last is not None:
            vpath = last + "/" + vpath
        pathlist.append(FileItem(vpath))
        last = vpath
    return pathlist

def decode_name(name):
    dirname = os.path.dirname(name)
    basename = os.path.basename(name)
    namepart, ext = os.path.splitext(basename)
    if ext in (".xenc", ".x0"):
        try:
            basename = base64.urlsafe_b64decode(namepart.encode("utf-8")).decode("utf-8")
            return os.path.join(dirname, basename)
        except:
            return name
    return name

def encode_name(name):
    namepart, ext = os.path.splitext(name)
    if ext in (".xenc", ".x0"):
        return name
    return base64.urlsafe_b64encode(name.encode("utf-8")).decode("utf-8") + ".x0"


def path_equals(source, target):
    """
        >>> path_equals('/home/a.txt', '/home/ccc/../a.txt')
        True
    """
    return os.path.abspath(source) == os.path.abspath(target)

def tmp_path(fname = "", prefix = "", ext = ""):
    """生成临时文件路径
    TODO 多线程情况下加锁
    """
    import xconfig
    if fname != None:
        return os.path.join(xconfig.TMP_DIR, fname)
    retry_times = 10
    name = prefix + time.strftime("%Y_%m_%d_%H%M%S")
    base_path = os.path.join(xconfig.TMP_DIR, name)
    path = base_path + ext
    for i in range(1, retry_times+1):
        if not os.path.exists(path):
            return path
        path = "%s_%s" % (base_path, i) + ext
    return None

def data_path(fname):
    """获取data目录文件路径
    """
    import xconfig
    return os.path.join(xconfig.DATA_DIR, fname)

def touch(path):
    """类似于Linux的touch命令"""
    if not os.path.exists(path):
        with open(path, "wb") as fp:
            pass
    else:
        current = time.mktime(time.gmtime())
        times = (current, current)
        os.utime(path, times)

def _search_path0(path, key, limit=200):
    result_dirs = []
    result_files = []
    key = key.lower()
    count = 0
    for root, dirs, files in os.walk(path):
        root_len = len(root)
        for f in dirs:
            abspath = os.path.join(root, f)
            if fnmatch(f.lower(), key):
                result_dirs.append(abspath)
                count+=1
                if count >= limit:
                    break
        for f in files:
            abspath = os.path.join(root, f)
            if fnmatch(f.lower(), key):
                result_files.append(abspath)
                count+=1
                if count >= limit:
                    break
        if count >= limit:
            break
    return result_dirs + result_files

def search_path(path, key):
    """搜索文件系统，key支持通配符表示，具体见fnmatch模块
    """
    result = []
    quoted_key = quote_unicode(key)
    if key != quoted_key:
        result = _search_path0(path, quoted_key)
    return result + _search_path0(path, key)


def backupfile(path, backup_dir = None, rename=False):
    if os.path.exists(path):
        if backup_dir is None:
            backup_dir = os.path.dirname(path)
        name   = os.path.basename(path)
        newname = name + ".bak"
        newpath = os.path.join(backup_dir, newname)
        # need to handle case that bakup file exists
        import shutil
        shutil.copyfile(path, newpath)


def get_upload_file_path(user, filename, upload_dir = "files", replace_exists = False):
    """生成上传文件名"""
    if xconfig.USE_URLENCODE:
        filename = quote_unicode(filename)
    basename, ext = os.path.splitext(filename)
    date = time.strftime("%Y/%m")
    dirname = os.path.join(xconfig.DATA_PATH, upload_dir, user, date)
    makedirs(dirname)

    origin_filename = os.path.join(dirname, filename)
    fileindex = 1

    newfilepath = origin_filename
    webpath = "/data/{}/{}/{}/{}".format(upload_dir, user, date, filename)
    if filename == "":
        # get upload directory
        return os.path.abspath(dirname), webpath

    while not replace_exists and os.path.exists(newfilepath):
        name, ext = os.path.splitext(filename)
        # 使用下划线，括号会使marked.js解析图片url失败
        temp_filename = "{}_{}{}".format(name, fileindex, ext)
        newfilepath = os.path.join(dirname, temp_filename)
        webpath = "/data/{}/{}/{}/{}".format(upload_dir, user, date, temp_filename)
        fileindex += 1
    return os.path.abspath(newfilepath), webpath

