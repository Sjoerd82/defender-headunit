#!/usr/bin/python

import re

sys.path.append('/mnt/PIHU_APP/defender-headunit/modules')
from hu_utils import *

list_of_paths = []
list_of_keys = []
path_dispatcher = {}

def special_disp(path_dispatch, cmd=None, args=None):
    path_dispatch = prepostfix(path_dispatch)
    # if there's an exact match, always handle that
    if path_dispatch in list_of_paths:
        path_dispatcher[path_dispatch](path=path_dispatch,cmd=cmd,args=args)
    else:
        for path,function in path_dispatcher.iteritems():
           wildpath = re.sub(r'\*',r'.*',path)
           if wildpath != path:
               res = re.search(wildpath,path_dispatch)
               if res is not None:
                   print res.group()
                   path_dispatcher[path](path=path_dispatch, cmd=cmd, args=args)
                   return True
    return False

def handle_mq(path,command=None): #path,*args,**kwargs):
    def decorator(fn):
        mq_path = path

        #prefix
        if not mq_path.startswith("/"):
            mq_path = "/"+path

        #postfix
        if not mq_path.endswith("/"):
            mq_path += "/"

        if command is None:
            key = mq_path
        else:
            key = command+mq_path

        list_of_paths.append(mq_path)
        list_of_keys.append(key)
        path_dispatcher[key] = fn
        def decorated(*args,**kwargs):
            #print "Hello from handl_mq decorator, your path is: {0}".format(path)
            #print path
            #print command
            #print args
            #print kwargs
            kwargs['path'] = 'Hello!'
            return fn(*args,**kwargs)
            #return fn(path,command)
        return decorated
    return decorator

@handle_mq('/some/one')
def Xyz(path=None,cmd=None,args=None):
    print "Xyz"

@handle_mq('/some/path', command="GET")
def foo(path=None,cmd=None,args=None):
    print "foo! {0}".format(command)

@handle_mq('/some/path', command="PUT")
def foo2(path=None,cmd=None,args=None):
    print "putting"

@handle_mq('/all/*')
def gimme(path=None,cmd=None,args=None):
    print "Executing the /all/* route"

@handle_mq('/all/*/test')
def gimmemore(path=None,cmd=None,args=None):
    print "Executing the /all/*/test route! path={0}".format(path)

@handle_mq('/all/test')
def gimmeX(path=None,cmd=None,args=None):
    print "Executing the /all/test route"

print list_of_paths
print path_dispatcher

special_disp('/all/test','GET')
special_disp('/all/blaa',args="blaat")
special_disp('/all/test/test')

#path_dispatcher['GET/some/path'](command="GET")
#path_dispatcher['PUT/some/path'](command="PUT")
#path_dispatcher['/some/one'](command="COOL")
#path_dispatcher['/all/test']()

#if 'COOL/some/one' in list_of_keys:
#    print "1"
#elif '/some/one' in list_of_keys:
#    print "2"
