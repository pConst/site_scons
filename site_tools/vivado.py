#-------------------------------------------------------------------------------
#
#    Xilinx Vivado Configuration Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import re

import SCons.Builder
import SCons.Scanner

from utils import *


#-------------------------------------------------------------------------------
#
#    Action functions
#
#---------------------------------------------------------------------
#
#    Build Tcl script to create OOC IP
#
def ip_create_script(target, source, env):

    src = source[0]
    trg = target[0]

    src_path = str(src)
    trg_path = str(trg)

    print_action('generate script:           \'' + trg.name + '\'')

    param_sect = 'config'

    ip_name = drop_suffix(src.name)
    ip_cfg  = read_ip_config(src_path, param_sect, env['CFG_PATH'])

    title_text =\
    'IP core "' + ip_name + '" create script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually,' + os.linesep + \
    'change parameters of IP in corresponing configuration file (cfg/ip/<IP name>)'

    text  = 'set ip_name    ' + ip_name                                   + os.linesep
    text += 'set DEVICE     ' + env['DEVICE']                             + os.linesep
    text += 'set IP_OOC_DIR ' + os.path.join(env['IP_OOC_PATH'], ip_name) + os.linesep*2
    text += 'set_part  ${DEVICE}'                                         + os.linesep
    text += 'create_ip -name ' + ip_cfg['type']
    text += ' -vendor xilinx.com'
    text += ' -library ip'
    text += ' -module_name ${ip_name}'
    text += ' -dir ${IP_OOC_DIR}'                                         + os.linesep*2

    ip_params  = ip_cfg[param_sect]
    max_pn_len = max_str_len(ip_params.keys())

    text += 'set_property -dict {' + os.linesep
    
    for p in ip_params:
        v = str(ip_params[p])
        if v == 'True' or v == 'False':
            v =  v.lower()
        v = '{' + v + '}'
        name_len      = len(p)
        value_len     = len(v)
        name_padding  = len(param_sect) + max_pn_len - name_len + 2
        line  = ' '*4 + param_sect + '.' + p + ' '*name_padding + v

        text += line + os.linesep

    text += '} [get_ips ${ip_name}]' + os.linesep
    
    text += os.linesep
    text += 'generate_target all [get_ips  ${ip_name}]'              + os.linesep
    text += 'export_simulation -of_objects [get_ips ${ip_name}] -simulator questa -absolute_path -force '
    text += '-directory ' + env['SIM_SCRIPT_PATH'] + os.linesep
    text += 'exit'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    with open(trg_path, 'w') as ofile:
        ofile.write(out)

    return None
#---------------------------------------------------------------------
#
#    Build Tcl script to synthesize OOC IP
#
def ip_syn_script(target, source, env):

    src = source[0]
    trg = target[0]

    src_path = str(src)
    trg_path = str(trg)

    print_action('generate script:           \'' + trg.name + '\'')

    with open(src_path) as src_f:
        ip_create_script = src_f.read()

    ip_name = drop_suffix(src.name)

    title_text =\
    'IP core "' + ip_name + '" synthesize script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually,' + os.linesep + \
    'change parameters of IP in corresponing configuration file (cfg/ip/<IP name>)'

    text  = 'set ip_name    ' + ip_name                                     + os.linesep
    text += 'set DEVICE     ' + env['DEVICE']                               + os.linesep
    text += 'set IP_OOC_DIR ' + env['IP_OOC_PATH']                          + os.linesep
    text += 'set OUT_DIR    [file join ${IP_OOC_DIR} ${ip_name}]'           + os.linesep*2
    text += 'set_part  ${DEVICE}'                                           + os.linesep

    if env['VIVADO_PROJECT_MODE']:
        text += 'create_project -force managed_ip_project '
        text += '${OUT_DIR}/ip_managed_project -p ${DEVICE} -ip'            + os.linesep

    text += 'read_ip   [file join ${IP_OOC_DIR} '
    text += '${ip_name} ${ip_name} ${ip_name}.' + env['IP_CORE_SUFFIX']+']' + os.linesep
    if env['VIVADO_PROJECT_MODE']:
        text += 'create_ip_run [get_ips ${ip_name}]'                        + os.linesep
        text += 'launch_runs -job 6 ${ip_name}_synth_1'                     + os.linesep
        text += 'wait_on_run ${ip_name}_synth_1'                            + os.linesep
        text += 'close_project'                                             + os.linesep
    else:
        text += 'synth_ip  [get_ips ${ip_name}]'                            + os.linesep
    text += 'exit'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    #print(out)

    with open(trg_path, 'w') as ofile:
        ofile.write(out)

    return None
#---------------------------------------------------------------------
#
#    Generate IP
#
def ip_create(target, source, env):

    src      = source[0]
    trg      = target[0]

    src_path = str(src)
    trg_path = str(trg)
    ip_name  = drop_suffix(trg.name)
    trg_dir  = os.path.join(env['IP_OOC_PATH'], ip_name)
    logfile  = os.path.join(trg_dir, 'create.log')

    print_action('create IP core:            \'' + trg.name + '\'')

    Execute( Delete(trg_dir) )
    Execute( Mkdir(trg_dir) )

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(' -source ' + os.path.abspath(src_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, trg_dir)

    return rcode

#---------------------------------------------------------------------
#
#    Run OOC IP synthesis
#
def ip_synthesize(target, source, env):

    src      = source[0]
    trg      = target[0]

    src_path = str(src)
    trg_path = str(trg)
    ip_name  = drop_suffix(trg.name)
    trg_dir  = os.path.join(env['IP_OOC_PATH'], ip_name)
    logfile  = os.path.join(trg_dir, 'syn.log')

    print_action('synthesize IP core:        \'' + trg.name + '\'')

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(' -source ' + os.path.abspath(src_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)
    rcode = pexec(cmd, trg_dir)

    return rcode

#---------------------------------------------------------------------
#
#    Create Configuration Parameters header
#
def cfg_params_header(target, source, env):

    trg      = target[0]
    trg_path = str(trg)

    print_action('create cfg params header:  \'' + trg.name + '\'')
    params = {}
    for src in source:
        cfg_params = read_config(str(src), search_root = env['CFG_PATH'])
        cfg_params = prefix_suffix(str(src), cfg_params)
        params.update(cfg_params)

    max_len = max_str_len(params.keys()) + 2
    guard   = 'GUARD_' + os.path.splitext(trg.name)[0].upper() + '_SVH'
    text  = generate_title('This file is automatically generated. Do not edit the file!', '//')
    text += '`ifndef ' + guard + os.linesep
    text += '`define ' + guard + os.linesep*2

    text += '// synopsys translate_off' + os.linesep
    text += '`ifndef SIMULATOR'         + os.linesep
    text += '`define SIMULATOR'         + os.linesep
    text += '`endif // SIMULATOR'       + os.linesep
    text += '// synopsys translate_on'  + os.linesep*2

    for p in params:
        text += '`define ' + p + ' '*(max_len - len(p)) + str(params[p]) + os.linesep

    text += os.linesep + '`endif // ' + guard + os.linesep
    text += generate_footer('//')

    with open(trg_path, 'w') as ofile:
        ofile.write(text)

    return None

#---------------------------------------------------------------------
#
#    Create Configuration Parameters Tcl
#
def cfg_params_tcl(target, source, env):

    trg      = target[0]
    trg_path = str(trg)

    print_action('create cfg params tcl:     \'' + trg.name + '\'')
    params = {}
    for src in source:
        cfg_params = read_config(str(src), search_root = env['CFG_PATH'])
        cfg_params = prefix_suffix(str(src), cfg_params)
        params.update(cfg_params)

    max_len = max_str_len(params.keys()) + 2

    text  = generate_title('This file is automatically generated. Do not edit the file!', '#')
    for p in params:
        value = str(params[p])
        if not value:
            value = '""'
        text += 'set ' + p + ' '*(max_len - len(p)) + value + os.linesep

    text += generate_footer('#')

    with open(trg_path, 'w') as ofile:
        ofile.write(text)

    return None

#---------------------------------------------------------------------
#
#    Create Vivado project
#
def vivado_project(target, source, env):

    trg          = str(target[0])
    trg_path     = os.path.abspath(trg)
    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )

    print_action('create Vivado project:     \'' + project_name + '\'')

    #-------------------------------------------------------
    #
    #   Classify sources
    #
    hdl     = []
    ip      = []
    xdc     = []
    tcl     = []
    incpath = env['INC_PATH']

    for s in source:
        s = str(s)
        if get_suffix(s) != env['IP_CORE_SUFFIX']:
            path   = search_file(s, env['CFG_PATH'])
            suffix = get_suffix(path)
            if suffix == env['TOOL_SCRIPT_SUFFIX']:
                tcl.append( os.path.abspath(path) )

            elif suffix == env['CONFIG_SUFFIX']:
                with open( path ) as f:
                    contents = yaml.safe_load(f)
                    if 'sources' in contents:
                        for item in contents['sources']:
                            src_suffix = get_suffix(item)
                            if src_suffix in [env['V_SUFFIX'], env['SV_SUFFIX']]:
                                fullpath = os.path.abspath(item)
                                hdl.append(fullpath)
                                incpath.append(os.path.dirname(fullpath))

                            if src_suffix in env['CONSTRAINTS_SUFFIX']:
                                xdc.append( os.path.abspath(item))
            else:
                print_error('E: unsupported file type. Only \'yml\', \'tcl\' file types supported')
                return -1

        else:
            ip.append(os.path.abspath(s))

    #-------------------------------------------------------
    #
    #   Delete old project
    #
    project_items = glob.glob(os.path.join(project_dir, project_name) + '*')
#   if os.path.exists(env['BD_SIM_PATH']):
#       project_items.append(env['BD_SIM_PATH'])
        
    for item in project_items:
        Execute( Delete(item) )

    #-------------------------------------------------------
    #
    #   Project create script
    #
    title_text =\
    'Vivado project "' + project_name + '" create script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'set PROJECT_NAME ' + env['VIVADO_PROJECT_NAME'] + os.linesep
    text += 'set TOP_NAME '     + env['TOP_NAME']            + os.linesep
    text += 'set DEVICE '       + env['DEVICE']              + os.linesep*2

    user_params = env['USER_DEFINED_PARAMS']
    for key in user_params:
        text += 'set ' + key + ' ' + user_params[key] + os.linesep

    project_create_args = [env['PROJECT_CREATE_FLAGS'], '${PROJECT_NAME}.' + env['VIVADO_PROJECT_SUFFIX'], '.']
        
    text += os.linesep
    text += '# Project structure'                                                                      + os.linesep
    text += 'create_project ' + ' '.join(project_create_args)                                          + os.linesep*2
    text += 'set_property FLOW "Vivado Synthesis ' + env['VIVADO_VERNUM'] + '" [get_runs synth_1]'     + os.linesep
    text += 'set_property FLOW "Vivado Implementation ' + env['VIVADO_VERNUM'] + '" [get_runs impl_1]' + os.linesep*2

    text += '# Add sources' + os.linesep
    text += 'puts "add HDL sources"' + os.linesep
    flist = ['    ' + h for h in hdl]
    text += 'add_files -scan_for_includes \\' + os.linesep
    text += (' \\' + os.linesep).join(flist)
    text += os.linesep*2

    text += '# Add constraints' + os.linesep
    text += 'puts "add constraints"' + os.linesep
    flist = ['    ' + x for x in xdc]
    text += 'add_files -fileset constrs_1 -norecurse \\'  + os.linesep
    text += (' \\' + os.linesep).join(flist)
    text += os.linesep*2

    text += os.linesep
    text += '# Add IP' + os.linesep
    text += 'puts "add IPs"' + os.linesep
    for i in ip:
        text += 'read_ip ' + i + os.linesep

    text += os.linesep
    text += '# Properties'                                                     + os.linesep
    text += 'set_property part ${DEVICE} [current_project]'                    + os.linesep
    text += 'set_property TARGET_SIMULATOR "Questa" [current_project]'         + os.linesep
    text += 'set_property include_dirs [lsort -unique [lappend incpath ' + \
             ' '.join(incpath) + ']] [get_filesets sources_1]'                 + os.linesep
    text += 'set_property top ${TOP_NAME} [get_filesets sources_1]'            + os.linesep
    text += os.linesep
    text += 'set_property used_in_simulation false [get_files  -filter {file_type == systemverilog} -of [get_filesets sources_1]]' + os.linesep
    text += 'set_property used_in_simulation false [get_files  -filter {file_type == verilog} -of [get_filesets sources_1]]'       + os.linesep
    text += os.linesep
    text += '# User-defined scripts' + os.linesep
    for t in tcl:
        text += 'source ' + t + os.linesep

    text += 'close_project' + os.linesep

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-create.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(str(project_dir), script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Create project
    #
    logfile  = os.path.join(project_dir, project_name + '-project-create.log')
    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, project_dir)
    if rcode:
        print_error('\n' + '*'*60)
        print_error('E: project create ends with error code, see log for details')
        print_error('*'*60 + '\n')
        Execute( Delete(project_path) )
        Execute( Delete(trg_path) )
        return -2
    else:
        Execute( Copy(trg_path, project_path) )
        print_success('\n' + '*'*35)
        print_success('Vivado project successfully created')
        print_success('*'*35 + '\n')

    return None

#---------------------------------------------------------------------
#
#    Synthesize Vivado project
#
def synth_vivado_project(target, source, env):

    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )

    print_action('synthesize Vivado project: \'' + project_name + '\'')
    #-------------------------------------------------------
    #
    #   Project build script
    #
    title_text =\
    'Vivado project "' + project_name + '" sythesize script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'open_project ' + project_path                                          + os.linesep

    text += os.linesep
    text += 'puts ""' + os.linesep
    text += 'puts "' + '\033\[1;33m>>>>>>>> Run Synthesis: Compiling and Mapping <<<<<<<<\\033\[0m' + '"' + os.linesep
    text += 'puts ""' + os.linesep

    text += os.linesep
    text += 'reset_run synth_1'                                                 + os.linesep
    text += 'launch_runs synth_1 -jobs 6'                                       + os.linesep
    text += 'wait_on_run synth_1'                                               + os.linesep
    text += 'if {[get_property PROGRESS [get_runs synth_1]] != "100%" } {'      + os.linesep
    text += '    error "\[XILINX_PRJ_BUILD:ERROR\] synth_1 failed"'             + os.linesep
    text += '} else {'                                                          + os.linesep
    text += '    puts "\[XILINX_PRJ_BUILD:INFO\] synth_1 completed. Ok."'       + os.linesep
    text += '}'                                                                 + os.linesep
    
    text += os.linesep
    text += 'close_project'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-synth.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(env['BUILD_SYN_PATH'], script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Run synthesize project
    #
    logfile  = os.path.join(env['BUILD_SYN_PATH'], project_name + '-project-synth.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, project_dir)
    if rcode:
        msg = 'E: project synthesis ends with error code, see log for details'
        print_error('\n' + '*'*len(msg))
        print_error(msg)
        print_error('*'*len(msg) + '\n')
        return -2
    else:
        msg = 'Vivado project successfully synthesized'
        print_success(os.linesep + '*'*len(msg))
        print_success(msg)
        print_success('*'*len(msg) + os.linesep)

    return None

#---------------------------------------------------------------------
#
#    Implement Vivado project
#
def impl_vivado_project(target, source, env):

    project_name = env['VIVADO_PROJECT_NAME']
    project_path = os.path.join(env['BUILD_SYN_PATH'], project_name + '.' + env['VIVADO_PROJECT_SUFFIX'])

    print_action('implement Vivado project:  \'' + project_name + '\'')
    #-------------------------------------------------------
    #
    #   Project build script
    #
    title_text =\
    'Vivado project "' + project_name + '" implement script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'open_project ' + project_path                                      + os.linesep

    text += os.linesep
    text += 'puts ""' + os.linesep
    text += 'puts "' + '\033\[1;33m>>>>>>>> Run Implementation: Place and Route <<<<<<<<\\033\[0m' + '"' + os.linesep
    text += 'puts ""' + os.linesep

    text += os.linesep
    text += 'reset_run impl_1'                                                  + os.linesep
    text += 'launch_runs impl_1 -jobs 6 -to_step write_bitstream'               + os.linesep
    text += 'wait_on_run impl_1'                                                + os.linesep
    text += 'if {[get_property PROGRESS [get_runs impl_1]] != "100%" } {'       + os.linesep
    text += '    error "\[XILINX_PRJ_BUILD:ERROR\] impl_1 failed"'              + os.linesep
    text += '} else {'                                                          + os.linesep
    text += '    puts "\[XILINX_PRJ_BUILD:INFO\] impl_1 completed. Ok."'        + os.linesep
    text += '}'                                                                 + os.linesep

    text += os.linesep
    text += 'close_project'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-impl.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(env['BUILD_SYN_PATH'], script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Run place&route project
    #
    logfile = os.path.join(env['BUILD_SYN_PATH'], project_name + '-project-impl.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)
        
    rcode = pexec(cmd, env['BUILD_SYN_PATH'])
    if rcode:
        msg = 'E: project build ends with error code, see log for details'
        print_error('\n' + '*'*len(msg))
        print_error(msg)
        print_error('*'*len(msg) + '\n')
    else:
        msg = 'Vivado project successfully implemented'
        print_success(os.linesep + '*'*len(msg))
        print_success(msg)
        print_success('*'*len(msg) + os.linesep)

    return None

#---------------------------------------------------------------------
#
#    Launch Vivado
#
def open_vivado_project(target, source, env):
    
    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )
    
        
#   src          = source[0]
#   srce = os.path.splitext(src)[0] + '.' + env['VIVADO_PROJECT_SUFFIX']
#   src_path     = os.path.abspath(str(src))
#   src_dir      = os.path.abspath(str(src.dir))
#   project_name = env['VIVADO_PROJECT_NAME']

    print_action('open Vivado project:       \'' + project_name + '\'')
    
    logfile  = os.path.join(project_dir, project_name + '-project-open.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))
    
    cmd = []
    cmd.append(env['SYNGUI'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(project_path)
    cmd = ' '.join(cmd)
    
    print(cmd)
    env.Execute('cd ' + project_dir + ' && ' + cmd + ' &')
    
    return None

#-------------------------------------------------------------------------------
#
#    Scanners
#
#---------------------------------------------------------------------
#
#    Config scanner
#
def scan_cfg_files(node, env, path):

    fname = str(node)
    with open(fname) as f:
        cfg = yaml.safe_load(f)

    if 'import' in cfg:
        imports = []
        for i in cfg['import'].split():
            fn = i + '.' + env['CONFIG_SUFFIX']
            found = False
            for p in path:
                full_path = os.path.join(p.path, fn)
                if os.path.exists(full_path):
                    imports.append(full_path)
                    found = True
                    break

            if not found:
                print_error('E: import config file ' + fn + ' not found')
                sys.exit(-2)

        return env.File(imports)

    else:
        return env.File([])
    
#---------------------------------------------------------------------
#
#    HDL scanner
#
def scan_hdl_files(node, env, path):

    pattern = '`include\s+\"(\w+\.\w+)\"'
           
    inclist = [] 
    contents = node.get_text_contents()
    includes = re.findall(pattern, contents)
    
    for i in includes:
        found = False
        for p in path:
            full_path = os.path.join( os.path.abspath(str(p)), i)
            if os.path.exists(full_path):
                inclist.append(full_path)
                found = True
                break

#       if not found:
#           print_error('E: include file ' + i + ' not found')
#           sys.exit(-2)
    
    return env.File(inclist)

#-------------------------------------------------------------------------------
#
#    Targets
#
def make_trg_nodes(src, src_suffix, trg_suffix, trg_dir, builder):

    s0 = src
    if SCons.Util.is_List(s0):
        s0 = str(s0[0])

    src_name = os.path.split(s0)[1]
    trg_name = src_name.replace(src_suffix, trg_suffix)
    trg      = os.path.join(trg_dir, trg_name)
    trg_list = builder(trg, src)

    #Depends(trg_list, 'top.scons')
    return trg_list

#---------------------------------------------------------------------
#
#    Processing OOC IP targets
#
def ip_create_scripts(env, src):
    res     = []
    src_sfx = '.'+env['CONFIG_SUFFIX']
    trg_sfx = '-create.'+env['TOOL_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    create_dirs([trg_dir])
    builder = env.IpCreateScript
    for i in src:
        res.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))

    return res
#---------------------------------------------------------------------
def ip_syn_scripts(env, src):
    res     = []
    src_sfx = '.'+env['CONFIG_SUFFIX']
    trg_sfx = '-syn.'+env['TOOL_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    builder = env.IpSynScript
    for i in src:
        res.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))

    return res
#---------------------------------------------------------------------
def create_ips(env, src):
    res     = []
    src_sfx = '-create.'+env['TOOL_SCRIPT_SUFFIX']
    trg_sfx = '.'+env['IP_CORE_SUFFIX']
    builder = env.IpCreate
    for i in src:
        ip_name = get_ip_name(i, src_sfx)
        trg_dir = os.path.join( env['IP_OOC_PATH'], ip_name, ip_name )
        res.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))

    return res
#---------------------------------------------------------------------
def syn_ips(env, src, deps=None):
    if deps:
        if len(src) != len(deps):
            print_error('E: ip_syn: src count:', len(src), 'must be equal deps count:', len(deps))
            sys.exit(2)

        src = list(zip(src, deps))
    else:
        print_error('E: ip_syn: "deps" argument (typically xci IP Core node list) not specified')
        sys.exit(2)

    res         = []
    script_sfx  = '-syn.'+env['TOOL_SCRIPT_SUFFIX']
    ip_core_sfx = '.' + env['IP_CORE_SUFFIX']
    trg_sfx     = '.'+env['DCP_SUFFIX']
    builder     = env.IpSyn
    for i in src:
        s = i[0]
        d = i[1]

        ip_name = get_ip_name(s, script_sfx)
        trg_dir = os.path.join( env['IP_OOC_PATH'], ip_name, ip_name )
        trg = make_trg_nodes(s + d, script_sfx, trg_sfx, trg_dir, builder)
        res.append(trg)

    return res
#---------------------------------------------------------------------
def create_cfg_params_header(env, trg, src):

    if not SCons.Util.is_List(src):
        src = src.split()
    source = []
    for s in src:
        ss = os.path.abspath(search_file(s))
        source.append(ss)

    env.CfgParamsHeader(trg, source)

    return trg
#---------------------------------------------------------------------
def create_cfg_params_tcl(env, trg, src):

    if not SCons.Util.is_List(src):
        src = src.split()
    source = []
    for s in src:
        ss = os.path.abspath(search_file(s))
        source.append(ss)

    env.CfgParamsTcl(trg, source)

    return trg
#---------------------------------------------------------------------
def create_vivado_project(env, src, ip_cores):

    trg_name = env['VIVADO_PROJECT_NAME'] + '.prj'
    target   = os.path.join(env['BUILD_SYN_PATH'], trg_name)

    if not SCons.Util.is_List(src):
        src = src.split()

    source   = []
    for s in src:
        if os.path.isabs(s):
            source.append(s)
            continue
        path = search_file(s)
        path = os.path.abspath(path)
        source.append(path)

    env.VivadoProject(target, source + ip_cores)

    return target

#---------------------------------------------------------------------
def launch_synth_vivado_project(env, prj, src):

    if not SCons.Util.is_List(prj):
        prj = prj.split()

    if not SCons.Util.is_List(src):
        src = src.split()

    prj_name = env['VIVADO_PROJECT_NAME']
    top_name = env['TOP_NAME']
    trg = os.path.join(env['BUILD_SYN_PATH'], prj_name + '.runs', 'synth_1', top_name + '.' + env['DCP_SUFFIX'])

    return env.SynthVivadoProject(trg, prj + src)

#---------------------------------------------------------------------
def launch_impl_vivado_project(env, src):

    prj_name = env['VIVADO_PROJECT_NAME']
    top_name = env['TOP_NAME']
    trg = os.path.join(env['BUILD_SYN_PATH'], prj_name + '.runs', 'impl_1', top_name + '.' + env['BITSTREAM_SUFFIX'])
    
    return env.ImplVivadoProject(trg, src)

#---------------------------------------------------------------------
def launch_open_vivado_project(env, src):
    
    return env.OpenVivadoProject('open_vivado_project', src)

#---------------------------------------------------------------------

#---------------------------------------------------------------------
#
#    Helper functions
#
def vivado_vernum(path):
    pattern = '(\d+)\.\d$'

    return re.search(pattern, path).groups()[0]

#---------------------------------------------------------------------
def get_suffix(path):
    return os.path.splitext(path)[1][1:]

#-------------------------------------------------------------------------------
#
#    Set up tool construction environment
#
def generate(env):

    Scanner = SCons.Scanner.Scanner
    Builder = SCons.Builder.Builder

    #-----------------------------------------------------------------
    #
    #    External Environment
    #
    if not 'XILINX_VIVADO' in env:
        env['XILINX_VIVADO'] = os.environ['XILINX_VIVADO']
        
    VIVADO = os.path.join(env['XILINX_VIVADO'], 'bin', 'vivado')
    
    #-----------------------------------------------------------------
    #
    #    Construction Variables
    #
    root_dir                     = str(env.Dir('#'))
    cfg_name                     = os.path.basename( os.getcwd() )

    env['VIVADO_VERNUM']         = vivado_vernum(env['XILINX_VIVADO'])
    env['VIVADO_PROJECT_NAME']   = 'vivado_project'
    env['TOP_NAME']              = 'top'
    env['DEVICE']                = 'xc7a200tfbg676-2'

    env['VIVADO_PROJECT_MODE']   = True

    env['SYNCOM']                = VIVADO + ' -mode batch '
    env['SYNSHELL']              = VIVADO + ' -mode tcl '
    env['SYNGUI']                = VIVADO + ' -mode gui '

    env['SYN_TRACE']             = ' -notrace'
    env['SYN_JOURNAL']           = ' -nojournal'
    env['PROJECT_CREATE_FLAGS']  = ''

    env['VERBOSE']               = True

    env['ROOT_PATH']             = os.path.abspath(str(Dir('#')))
    env['CFG_PATH']              = os.path.abspath(os.curdir)  # current configuration path
    env['SETTINGS_SEARCH_PATH']  = env['CFG_PATH']
    env['BUILD_SRC_PATH']        = os.path.join(root_dir, 'build', cfg_name, 'src')
    env['BUILD_SYN_PATH']        = os.path.join(root_dir, 'build', cfg_name, 'syn')
    env['IP_OOC_PATH']           = os.path.join(env['BUILD_SYN_PATH'], 'ip_ooc')
    env['INC_PATH']              = ''

    env['IP_SCRIPT_DIRNAME']     = '_script'
    env['SIM_SCRIPT_DIRNAME']    = 'sim_script'
    env['SIM_SCRIPT_PATH']       = os.path.join(env['BUILD_SYN_PATH'], env['SIM_SCRIPT_DIRNAME'])

    env['CONFIG_SUFFIX']         = 'yml'
    env['TOOL_SCRIPT_SUFFIX']    = 'tcl'
    env['IP_CORE_SUFFIX']        = 'xci'
    env['DCP_SUFFIX']            = 'dcp'
    env['BITSTREAM_SUFFIX']      = 'bit'
    env['CONSTRAINTS_SUFFIX']    = 'xdc'
    env['VIVADO_PROJECT_SUFFIX'] = 'xpr'
    env['V_SUFFIX']              = 'v'
    env['SV_SUFFIX']             = 'sv'
    env['V_HEADER_SUFFIX']       = 'vh'
    env['SV_HEADER_SUFFIX']      = 'svh'

    env['USER_DEFINED_PARAMS']   = {}

    env.Append(SYNFLAGS = env['SYN_TRACE'])
    env.Append(SYNFLAGS = env['SYN_JOURNAL'])


    #-----------------------------------------------------------------
    #
    #   Scanners
    #
    CfgImportScanner = Scanner(name  = 'CfgImportScanner',
                       function      = scan_cfg_files,
                       skeys         = ['.' + env['CONFIG_SUFFIX']],
                       recursive     = True,
                       path_function = SCons.Scanner.FindPathDirs('SETTINGS_SEARCH_PATH')
                      )

    HdlSourceScanner = Scanner(name  = 'HldSourceScanner',
                       function      = scan_hdl_files,
                       skeys         = ['.' + env['V_SUFFIX'], '.' + env['SV_SUFFIX']],
                       recursive     = True,
                       path_function = SCons.Scanner.FindPathDirs('INC_PATH')
                      )
    #-----------------------------------------------------------------
    #
    #   Builders
    #
    IpCreateScript     = Builder(action         = ip_create_script,
                                 suffix         = env['TOOL_SCRIPT_SUFFIX'],
                                 #src_suffix     = env['IP_CONFIG_SUFFIX'],
                                 source_scanner = CfgImportScanner)

    IpSynScript        = Builder(action         = ip_syn_script,
                                 suffix         = env['TOOL_SCRIPT_SUFFIX'],
                                 source_scanner = CfgImportScanner)


    IpCreate           = Builder(action     = ip_create,
                                 suffix     = env['IP_CORE_SUFFIX'],
                                 src_suffix = env['TOOL_SCRIPT_SUFFIX'])

    IpSyn              = Builder(action     = ip_synthesize,
                                 suffix     = env['DCP_SUFFIX'],
                                 src_suffix = env['IP_CORE_SUFFIX'])

    CfgParamsHeader    = Builder(action = cfg_params_header, source_scanner = CfgImportScanner)
    CfgParamsTcl       = Builder(action = cfg_params_tcl,    source_scanner = CfgImportScanner)

    VivadoProject      = Builder(action = vivado_project)

    SynthVivadoProject = Builder(action = synth_vivado_project, source_scanner = HdlSourceScanner)
    ImplVivadoProject  = Builder(action = impl_vivado_project)
    
    
    OpenVivadoProject  = Builder(action = open_vivado_project)

    Builders = {
        'IpCreateScript'      : IpCreateScript,
        'IpSynScript'         : IpSynScript,
        'IpCreate'            : IpCreate,
        'IpSyn'               : IpSyn,
        'CfgParamsHeader'     : CfgParamsHeader,
        'CfgParamsTcl'        : CfgParamsTcl,
        'VivadoProject'       : VivadoProject,

        'SynthVivadoProject'  : SynthVivadoProject,
        'ImplVivadoProject'   : ImplVivadoProject,
        
        'OpenVivadoProject'   : OpenVivadoProject
    }

    env.Append(BUILDERS = Builders)

    #-----------------------------------------------------------------
    #
    #   IP core processing pseudo-builders
    #
    env.AddMethod(ip_create_scripts, 'IpCreateScripts')
    env.AddMethod(ip_syn_scripts,    'IpSynScripts')
    env.AddMethod(create_ips,        'CreateIps')
    env.AddMethod(syn_ips,           'SynIps')

    env.AddMethod(create_cfg_params_header,    'CreateCfgParamsHeader')
    env.AddMethod(create_cfg_params_tcl,       'CreateCfgParamsTcl')
    env.AddMethod(create_vivado_project,       'CreateVivadoProject')

    env.AddMethod(launch_synth_vivado_project, 'LaunchSynthVivadoProject')
    env.AddMethod(launch_impl_vivado_project,  'LaunchImplVivadoProject')

    env.AddMethod(launch_open_vivado_project,  'LaunchOpenVivadoProject')


#-------------------------------------------------------------------------------
def exists(env):
    print('vivado-npf tool: exists')
#-------------------------------------------------------------------------------

