#!/usr/bin/env python
'''
    yoctotrace.py: Linux kernel ftrace wrapper for tracing 
                   a particular Linux kernel module.

    This utility provides a wrapper to Linux's debugfs.  Since the latter
    filesystem is being manipulated this tool should be run with appropriate
    privileges.

    Yes, there are other tools like this, however, I want to keep things simple
    and make use of this for my specific purposes.

    Example:
        // This utility runs both a count and callgraph (timing) trace.
        // Only one or the other test can be performed, not both
        // simultaneously.
        //
        // Once you desire the trace to end, issue a '--stop' or '-s' to
        // yoctotrace.py.          //
        // The results will be generated to a temporary file
        // ftrace.scan.N where N is a number

        sudo ./yoctotrace.py -c -d /sys/kernel/debug -m my_awesome_module

        ... do some crap ...

        sudo ./ypctotrace.py -s

    Resources:
        https://www.kernel.org/doc/Documentation/trace/ftrace.txt
        https://lwn.netcArticles/365835/ (Ftrace Part 1)
        https://lwn.net/Articles/366796/ (Ftrace Part 2)
'''
import argparse, os, subprocess, sys


debug = True 


# Tracer class (one per tracing type)
class Tracer(object):
    def __init__(self, description, debugfs_path, ftrace_name, module=None):
        self.path = debugfs_path
        self.desc = description
        self.module = module
        self.ftrace_name = ftrace_name

        # Set the filter (echo ':mod:somemodule' > debugfs/set_function_filter)
	if module:
	    call_cmd(self.path, 'set_ftrace_filter', '\':mod:'+self.module+'\'')

	# Enable the tracer (echo trace_name > debugfs/current_tracer)
        call_cmd(self.path, 'current_tracer', self.ftrace_name)

        # Enable counts if we have no tracer
        # (echo 1 > debugfs/function_profile_enabled)
        call_cmd(self.path, 'function_profile_enabled',
                 int(self.ftrace_name == 'nop'))
        

# Send a command to the shell
def call_cmd(path, dest_file, val):
    cmd = 'echo ' + str(val) + ' > ' + os.path.join(path, dest_file)
    if debug == True:
        print("(yoctotrace.py) Issuing command: " + cmd)
        subprocess.call(cmd, shell=True)


# Start (1) or Stop (0) and dump the trace
# (echo 1 or 0 > debugfs/tracing_on)
def toggle_trace(path, enable):
    call_cmd(path, 'tracing_on', enable) 


# Reset trace log (echo nop > debugfs/current_tracer)
def reset_trace(path):
    call_cmd(path, 'current_tracer', 'nop')


# Dump the results to file
def dump_results(path):
    for i in range(1000):
        fname = './ftrace.log.' + str(i)
        if os.path.exists(fname):
            continue
        else:
            break
    print('Dumping results to ' + fname)
    cmd = 'cat ' + os.path.join(path, 'trace') + ' > ' + fname
    subprocess.call(cmd, shell=True)
    cmd = 'cat ' + os.path.join(path, 'trace_stat/function*') + ' >> ' + fname
    subprocess.call(cmd, shell=True)



if __name__ == '__main__':
    parse = argparse.ArgumentParser(description='Enable function counting '+\
                                                'and timing via Linux ftrace')
    parse.add_argument('-c', '--count', action='store_true',
                       help='Generate a count of functions called')
    parse.add_argument('-g', '--callgraph', action='store_true',
                       help='Generate a function call graph (with timings)')
    parse.add_argument('-m', '--module', nargs=1,
                       help='Module name to trace')
    parse.add_argument('-s', '--stop', action='store_true',
                       help='Stop the trace and generate report to a '+\
                            'file in the current working dir named '  +\
                            'ftrace.log.N')
    parse.add_argument('-d', '--debugfs', default='/sys/kernel/debug',
                       help='Path to the debugfs directory ' +\
                            '(default: /sys/kernel/debug)')
    args = parse.parse_args()

    # Check argument sanity
    if len(sys.argv) == 1:
	parse.print_help()
	sys.exit(0)
    elif (args.count or args.callgraph) and args.module == None:
        print('A module to trace must be specified')
        sys.exit(-1)
    elif (args.count or args.callgraph) and args.stop == True:
        print('You cannot trace and stop a trace at the same time! '+\
              'Illogical! -Spock')
        sys.exit(-1)
    elif (args.count and args.callgraph):
        print('Sorry Dave, I cannot let you perform '+\
              'multiple trace styles at once')
        sys.exit(-1)

    # The arguments appear to be sane. Make sure we actually have a debugfs!
    path = os.path.join(args.debugfs, 'tracing')
    if not os.path.exists(path):
        print('Cannot locate debugfs at: ' + path)
        sys.exit(-1)

     # If we are to stop recording/tracing
    if args.stop:
        toggle_trace(path, 0)
        dump_results(path)
        sys.exit(0)
    else: # Else perform normal tracing
        toggle_trace(path, 0)
        if args.callgraph:
            Tracer(description='Function callgraph trace',
                   debugfs_path=path,
                   ftrace_name='function_graph',
                   module=args.module[0])
        if args.count:
            Tracer("Enabling callgraph trace",
                   debugfs_path=path,
                   ftrace_name='nop')
        toggle_trace(path, 1)
