import imp, os, sys

class UnicodeImporter(object):
    def find_module(self,fullname,path=None):
        if isinstance(fullname,unicode):
            fullname = fullname.replace(u'.',u'\\')
            exts = (u'.pyc',u'.pyo',u'.py')
        else:
            fullname = fullname.replace('.','\\')
            exts = ('.pyc','.pyo','.py')
        if os.path.exists(fullname) and os.path.isdir(fullname):
            return self
        for ext in exts:
            if os.path.exists(fullname+ext):
                return self

    def load_module(self,fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        else: # set to avoid reimporting recursively
            sys.modules[fullname] = imp.new_module(fullname)
        if isinstance(fullname,unicode):
            filename = fullname.replace(u'.',u'\\')
            ext = u'.py'
            initfile = u'__init__'
        else:
            filename = fullname.replace('.','\\')
            ext = '.py'
            initfile = '__init__'
        try:
            if os.path.exists(filename+ext):
                with open(filename+ext,'U') as fp:
                    mod = imp.load_source(fullname,filename+ext,fp)
                    sys.modules[fullname] = mod
                    mod.__loader__ = self
            else:
                mod = sys.modules[fullname]
                mod.__loader__ = self
                mod.__file__ = os.path.join(os.getcwd(),filename)
                mod.__path__ = [filename]
                #init file
                initfile = os.path.join(filename,initfile+ext)
                if os.path.exists(initfile):
                    with open(initfile,'U') as fp:
                        code = fp.read()
                    exec compile(code, initfile, 'exec') in mod.__dict__
            return mod
        except Exception as e: # wrap in ImportError a la python2 - will keep
            # the original traceback even if import errors nest
            print 'fail', filename+ext
            raise ImportError, u'caused by ' + repr(e), sys.exc_info()[2]

if not hasattr(sys,'frozen'):
    sys.meta_path = [UnicodeImporter()]

if __name__ == '__main__':
    from mainprogram import courcesdemo
    courcesdemo.main()
